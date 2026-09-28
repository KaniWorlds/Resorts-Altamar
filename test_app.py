import concurrent.futures
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
import app


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = app.DATABASE
        app.DATABASE = Path(self.temp.name) / 'test.sqlite3'
        app.initialize()
        self.data = {'guest': 'Cliente de prueba', 'hotel_id': 1,
                     'arrival': date.today().isoformat(),
                     'departure': (date.today() + timedelta(days=2)).isoformat()}

    def tearDown(self):
        app.DATABASE = self.original
        self.temp.cleanup()

    def test_twenty_hotels(self):
        with app.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM hotels').fetchone()[0], 20)

    def test_create_and_cancel_releases_inventory(self):
        rid = app.create_reservation(self.data)['id']
        app.cancel_reservation(rid)
        with app.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM nights').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT status FROM reservations').fetchone()[0], 'Cancelada')

    def test_concurrent_requests_cannot_overbook(self):
        def attempt(_):
            try:
                app.create_reservation(self.data)
                return True
            except ValueError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(attempt, range(12)))
        self.assertEqual(sum(results), 5)
        with app.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM nights').fetchone()[0], 10)

    def test_departure_day_is_available(self):
        for _ in range(5):
            app.create_reservation(self.data)
        following = {**self.data, 'arrival': self.data['departure'],
                     'departure': (date.today() + timedelta(days=3)).isoformat()}
        self.assertTrue(app.create_reservation(following)['id'])

    def test_invalid_dates_and_hotel(self):
        for data in [{**self.data, 'departure': self.data['arrival']},
                     {**self.data, 'hotel_id': 999}, {**self.data, 'guest': ''}]:
            with self.assertRaises(ValueError):
                app.create_reservation(data)


if __name__ == '__main__':
    unittest.main()
