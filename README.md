# Resorts Altamar - base simple

Aplicación local para crear, listar y cancelar reservas. Incluye 20 hoteles en 4 regiones, con 5 habitaciones de demostración por hotel. Los datos se guardan en `altamar.sqlite3`, creado al iniciar.

## Abrir

En Windows, haz doble clic en **INICIAR.bat**. Necesita Python 3.11 o posterior; no necesita instalar paquetes. El iniciador también reconoce el Python incluido con Codex en este equipo.

O ejecuta desde esta carpeta:

```sh
python app.py --open
```

Abre http://127.0.0.1:8080. Mantén la consola abierta mientras lo usas. Para detenerlo, presiona Ctrl+C en la consola. No abras `index.html` directamente: necesita el servidor.

## Probar

1. Crea una reserva con nombre, hotel y fechas.
2. Aparecerá en el registro con una habitación asignada.
3. Reserva las mismas fechas cinco veces en el mismo hotel. La sexta solicitud se rechaza.
4. Cancela una reserva: el cupo queda disponible de nuevo.

La salida no ocupa una noche: una persona puede salir el día en que otra llega. La estadía admite entre 1 y 60 noches. La base de datos bloquea las escrituras concurrentes antes de consultar cupos y una clave única por hotel, habitación y noche impide duplicarlos.

## Archivos

- `app.py`: servidor, base de datos y reglas de reservas.
- `static/index.html`: formulario y listado.
- `static/style.css`: apariencia y adaptación a pantallas pequeñas.
- `static/app.js`: conexión del formulario con el servidor.
- `test_app.py`: pruebas de las reglas principales.

Ejecuta las pruebas con `python -m unittest -v`. Usan una base temporal y no modifican tus reservas.

## Alcance

Versión reducida a petición del usuario, basada en el caso Resorts Altamar. No incluye usuarios/roles, RUT, servicios, check-in/check-out, modificaciones de reserva, sugerencias automáticas ni facturación. Cualquier persona que use esta aplicación local puede ver y cancelar todas las reservas. No está publicada en Internet y no representa el cumplimiento completo de la rúbrica EV03.
