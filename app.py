"""Base local de Resorts Altamar. Solo requiere Python 3.11 o posterior."""
import json
import sqlite3
import webbrowser
from contextlib import contextmanager
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / 'altamar.sqlite3'


@contextmanager
def connection():
    db = sqlite3.connect(DATABASE, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize():
    with connection() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS hotels(
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, region TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reservations(
                id INTEGER PRIMARY KEY, hotel_id INTEGER NOT NULL REFERENCES hotels(id),
                guest TEXT NOT NULL, arrival TEXT NOT NULL, departure TEXT NOT NULL,
                room INTEGER NOT NULL CHECK(room BETWEEN 1 AND 5),
                status TEXT NOT NULL DEFAULT 'Confirmada', CHECK(departure > arrival));
            CREATE TABLE IF NOT EXISTS nights(
                hotel_id INTEGER NOT NULL REFERENCES hotels(id), room INTEGER NOT NULL,
                night TEXT NOT NULL, reservation_id INTEGER NOT NULL REFERENCES reservations(id),
                PRIMARY KEY(hotel_id, room, night));
        ''')
        if not db.execute('SELECT 1 FROM hotels LIMIT 1').fetchone():
            regions = {
                'Norte': ['Arica', 'Iquique', 'Antofagasta', 'Caldera', 'La Serena'],
                'Centro': ['Concón', 'Viña del Mar', 'Valparaíso', 'Algarrobo', 'Pichilemu'],
                'Sur': ['Pucón', 'Villarrica', 'Valdivia', 'Puerto Varas', 'Frutillar'],
                'Austral': ['Castro', 'Chaitén', 'Coyhaique', 'Puerto Natales', 'Punta Arenas'],
            }
            db.executemany('INSERT INTO hotels(name,region) VALUES(?,?)',
                           [('Altamar ' + city, region) for region, cities in regions.items() for city in cities])


def create_reservation(data):
    guest = data.get('guest', '')
    if not isinstance(guest, str) or not 2 <= len(guest.strip()) <= 80:
        raise ValueError('Escribe un nombre de 2 a 80 caracteres.')
    try:
        hotel = int(data['hotel_id'])
        arrival, departure = date.fromisoformat(data['arrival']), date.fromisoformat(data['departure'])
    except (KeyError, ValueError, TypeError):
        raise ValueError('Selecciona un hotel y fechas válidas.')
    if arrival < date.today() or not 1 <= (departure - arrival).days <= 60:
        raise ValueError('La llegada debe ser hoy o después y la estadía debe durar entre 1 y 60 noches.')
    with connection() as db:
        # El bloqueo precede a la consulta: dos solicitudes no pueden tomar el mismo cupo.
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM hotels WHERE id=?', (hotel,)).fetchone():
            raise ValueError('El hotel no existe.')
        occupied = {r[0] for r in db.execute(
            'SELECT DISTINCT room FROM nights WHERE hotel_id=? AND night>=? AND night<?',
            (hotel, arrival.isoformat(), departure.isoformat()))}
        room = next((n for n in range(1, 6) if n not in occupied), None)
        if room is None:
            raise ValueError('No quedan habitaciones en ese hotel para esas fechas. Prueba otro hotel o rango de fechas.')
        rid = db.execute('INSERT INTO reservations(hotel_id,guest,arrival,departure,room) VALUES(?,?,?,?,?)',
                         (hotel, guest.strip(), arrival.isoformat(), departure.isoformat(), room)).lastrowid
        db.executemany('INSERT INTO nights VALUES(?,?,?,?)',
                       [(hotel, room, (arrival + timedelta(days=i)).isoformat(), rid)
                        for i in range((departure - arrival).days)])
        return {'message': f'Reserva ALT-{rid:04d} creada. Habitación {room}.', 'id': rid}


def cancel_reservation(rid):
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT status FROM reservations WHERE id=?', (rid,)).fetchone()
        if not row:
            raise ValueError('La reserva no existe.')
        if row['status'] == 'Cancelada':
            raise ValueError('La reserva ya está cancelada.')
        db.execute("UPDATE reservations SET status='Cancelada' WHERE id=?", (rid,))
        db.execute('DELETE FROM nights WHERE reservation_id=?', (rid,))
    return {'message': 'Reserva cancelada. La habitación vuelve a estar disponible.'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status, data, mime='application/json; charset=utf-8'):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        files = {'/': ('index.html', 'text/html'), '/style.css': ('style.css', 'text/css'),
                 '/app.js': ('app.js', 'text/javascript'), '/favicon.svg': ('favicon.svg', 'image/svg+xml')}
        if path in files:
            filename, mime = files[path]
            return self.reply(200, (ROOT / 'static' / filename).read_bytes(), mime + '; charset=utf-8')
        with connection() as db:
            if path == '/api/hotels':
                rows = db.execute('SELECT * FROM hotels ORDER BY id').fetchall()
            elif path == '/api/reservations':
                rows = db.execute('''SELECT r.*, h.name hotel FROM reservations r
                    JOIN hotels h ON h.id=r.hotel_id ORDER BY r.id DESC''').fetchall()
            else:
                return self.reply(404, {'error': 'Página no encontrada.'})
        self.reply(200, [dict(r) for r in rows])

    def do_POST(self):
        try:
            # Esta base es local; no acepta solicitudes de otros sitios.
            host = self.headers.get('Host', '')
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if host not in allowed or self.headers.get('Origin', 'http://' + host) != 'http://' + host:
                return self.reply(403, {'error': 'Origen no permitido.'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.reply(415, {'error': 'Se requiere JSON.'})
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise ValueError('El formulario está vacío o es demasiado grande.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Formulario inválido.')
            if self.path == '/api/reservations':
                result = create_reservation(data)
            elif self.path == '/api/cancel':
                result = cancel_reservation(int(data.get('id', 0)))
            else:
                return self.reply(404, {'error': 'Operación no encontrada.'})
            self.reply(200, result)
        except (ValueError, TypeError, UnicodeDecodeError) as error:
            self.reply(400, {'error': str(error)})
        except sqlite3.Error:
            self.reply(409, {'error': 'No se pudo guardar la reserva. Actualiza e inténtalo nuevamente.'})


if __name__ == '__main__':
    import sys
    initialize()
    server = ThreadingHTTPServer(('127.0.0.1', 8080), Handler)
    print('Altamar: http://127.0.0.1:8080 — Ctrl+C para cerrar.', flush=True)
    if '--open' in sys.argv:
        webbrowser.open('http://127.0.0.1:8080')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
