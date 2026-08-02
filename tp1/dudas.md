## Docker Compose: `up` vs `run` para la TUI interactiva

`docker compose up --build` levanta el contenedor correctamente (recolector, analizadores y agregador funcionan), pero el teclado no responde en la TUI. Es una limitación conocida de Docker Compose: `up` no adjunta stdin al contenedor, solo stdout/stderr (incluso con `tty: true` y `stdin_open: true`, y con un solo servicio). `docker compose run --rm monitor` sí adjunta stdin correctamente, como `docker run -it`.

No encontré una forma de que `up` (comando único, sin pasos extra) reconozca el teclado. 

