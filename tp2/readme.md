# TP2 — Plataforma de tareas distribuidas

Servicio HTTP (FastAPI) que recibe tareas, las encola y las ejecuta en un pool de workers con `asyncio`. Soporta tres
tipos de tarea: `descargar` (I/O-bound), `hashear` (CPU-bound) y `esperar` (I/O simulado). Cancelación real de tareas
en ejecución, timeouts por tarea, apagado ordenado con volcado del estado a JSON y todo empaquetado con Docker.

Computación II — Universidad de Mendoza. Trabajo individual.

## 1. Cómo se usa

### Con Docker (lo pedido por la consigna)

```bash
cd tp2
docker compose up --build        # la API queda en http://localhost:8000
```

Documentación interactiva: <http://localhost:8000/docs>. Para apagar: `Ctrl+C` (o `docker compose stop`), que dispara el
apagado ordenado y deja un `estado_<timestamp>.json` en `tp2/datos/`.

### Sin Docker (Python 3.12)

```bash
cd tp2
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main --workers 4 --puerto 8000
```

### Ejemplos con `curl`

```bash
# Encolar (responde 201 al instante con el id y estado "pendiente")
curl -s -X POST localhost:8000/tareas -H 'content-type: application/json' \
     -d '{"tipo":"esperar","segundos":20}'
curl -s -X POST localhost:8000/tareas -H 'content-type: application/json' \
     -d '{"tipo":"hashear","texto":"hola","iteraciones":5000000,"prioridad":5}'
curl -s -X POST localhost:8000/tareas -H 'content-type: application/json' \
     -d '{"tipo":"descargar","urls":["https://example.com","https://httpbin.org/delay/1"],"timeout":15}'

curl -s localhost:8000/tareas                       # listar
curl -s "localhost:8000/tareas?estado=ejecutando"   # filtrar por estado
curl -s localhost:8000/tareas/1                     # estado y resultado
curl -s -X DELETE localhost:8000/tareas/1           # cancelar (encolada o en ejecución)
curl -s localhost:8000/estadisticas                 # totales, tiempos promedio, workers ocupados
```

| Método | Ruta | Qué hace |
|---|---|---|
| `POST` | `/tareas` | Encola. `201` con el id; `422` si el cuerpo es inválido; `503` + `Retry-After` si la cola está llena o el servicio se apaga |
| `GET` | `/tareas` | Lista (filtro `?estado=` y `?limite=`) |
| `GET` | `/tareas/{id}` | Estado y resultado; `404` si no existe |
| `DELETE` | `/tareas/{id}` | Cancela; `409` si ya terminó |
| `GET` | `/estadisticas` | Totales por estado, cola, workers ocupados, tiempos promedio, fds/threads/RSS del proceso |

Estados: `pendiente`, `ejecutando`, `completada`, `fallida`, `cancelada`. Cada tarea acepta `prioridad` (1–5, mayor sale
primero) y `timeout` en segundos.

### Configuración

Cada opción se puede dar por flag o por variable de entorno (prioridad: flag > entorno > valor por defecto):

| Opción | Por defecto | Qué controla |
|---|---|---|
| `--workers` | 4 | Corrutinas consumidoras de la cola |
| `--cola-max` | 1000 | Capacidad de la cola (más allá: `503`) |
| `--timeout-default` | 30 | Segundos por tarea si el pedido no trae uno |
| `--procesos` | nº de CPUs | Procesos del `ProcessPoolExecutor` (hash) |
| `--chunk-hash` | 200000 | Iteraciones de hash por viaje al executor |
| `--max-conexiones` | 100 | Tope de descargas simultáneas en todo el servicio |
| `--apagado-timeout` | 10 | Espera máxima por las tareas en curso al apagar |
| `--datos-dir` | `datos` | Carpeta de los volcados |
| `--hash-bloqueante` | false | Solo para la medición 2: hashea dentro del loop |

### Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## 2. Arquitectura

```
                    ┌─────────────────────────────── un solo proceso, un solo event loop ───────────────────────────────┐
  cliente  ──HTTP──▶│ FastAPI (uvicorn)                                                                                 │
                    │   POST /tareas ──▶ Registro (dict id→Tarea) ──▶ ColaTareas (asyncio.PriorityQueue, acotada)        │
                    │   GET/DELETE ◀──────────┘                              │ obtener()                                │
                    │                                                        ▼                                          │
                    │                                  Pool: N workers (corrutinas) ── cada tarea en su propia Task      │
                    │                                        │            │             │                               │
                    │                                  esperar      descargar         hashear                           │
                    │                              asyncio.sleep   httpx.AsyncClient   run_in_executor ──▶ ProcessPool  │
                    └────────────────────────────────────────────────────────────────────────────────────────────────────┘
  SIGTERM/SIGINT ─▶ no aceptar tareas nuevas ─▶ esperar (con límite) a las en curso ─▶ volcar estado_<timestamp>.json
```

Flujo de una tarea:

1. `POST /tareas` valida el cuerpo (Pydantic, unión discriminada por `tipo`), crea la `Tarea` en estado `pendiente`, la
   mete en la cola y responde `201` **sin esperar**.
2. Un worker libre saca el id de la cola (mayor prioridad primero, FIFO entre iguales), la pasa a `ejecutando` y lanza su
   ejecutor en una `asyncio.Task` propia, envuelta en `asyncio.wait_for(timeout)`.
3. Al terminar queda `completada`, `fallida` (excepción o timeout, con el motivo) o `cancelada`.

Estructura del código (`tp2/src`): `api.py` (endpoints), `app.py` (lifespan: crea y cierra todos los recursos),
`main.py` (arranque y señales), `config.py`, `modelos.py` (validación), `estado.py` (registro de tareas),
`cola.py`, `workers.py` (pool), `persistencia.py` (volcado JSON) y `tareas/` (los tres ejecutores).

## 3. Decisiones de diseño

**¿Por qué `asyncio.Queue` y no `queue.Queue`?** Porque `get()` y `put()` de `asyncio.Queue` son corrutinas: un worker
sin trabajo *cede* el event loop en lugar de bloquear el hilo. Con `queue.Queue`, un solo `get()` bloqueante congelaría
todo el servicio, ya que todas las corrutinas comparten un hilo. Además es una cola de prioridad con `maxsize`: cuando se
llena, `put_nowait` lanza `QueueFull` y la API responde `503` con `Retry-After` (backpressure) en vez de crecer sin
límite hasta agotar la memoria.

**¿Cómo evito que una tarea CPU-bound congele la API?** `hashear` no corre en el event loop: cada trozo de
`chunk_hash` iteraciones viaja con `loop.run_in_executor` a un `ProcessPoolExecutor`. Se usan procesos y no threads
porque SHA-256 en un bucle de Python retiene el GIL (clase 14): un thread seguiría compitiendo con el loop por el GIL,
mientras que un proceso tiene su propio intérprete y usa otro núcleo. Se trocea para poder cancelar: un job que ya corre
en otro proceso no se puede interrumpir, pero entre trozo y trozo el `await` sí es un punto de cancelación y el proceso
nunca sigue calculando más de un trozo. La función `paso` es de módulo para ser *picklable*.

**¿Cómo funciona la cancelación y qué pasa con los recursos a medio usar?** Cada tarea corre en su propia `Task`
(`inner`), distinta de la del worker. `DELETE` hace `inner.cancel()`: el `CancelledError` se levanta en el `await` donde
estaba la tarea, y el worker lo atrapa y sigue vivo con la próxima. Una tarea todavía `pendiente` se marca `cancelada` y el
worker la saltea al sacarla de la cola (la cola no permite sacar elementos del medio). Para distinguir "cancelaron la
tarea" de "cancelaron al worker" (apagado) se usa `current_task().cancelling()`: si es mayor que 0 se vuelve a lanzar la
excepción. Sobre los recursos: en `descargar`, `gather` cancela a todas las descargas hijas y `httpx` cierra sus
conexiones; el semáforo se libera con `async with`; y en `hashear` el trozo en vuelo termina en el proceso y se descarta.
`finally` garantiza que ninguna tarea quede en `ejecutando` y que `task_done()` se llame siempre.

**¿Qué pasa si un worker lanza una excepción no capturada?** Hay tres capas. (1) Los ejecutores no pueden tirar al worker:
`_ejecutar` atrapa `Exception` y la tarea queda `fallida` con el motivo. (2) Un bug propio dentro del bucle del worker se
loguea con `log.exception` y el worker sigue con la próxima. (3) Si aun así el worker muriera, un `add_done_callback` lo
detecta, lo loguea y lanza un reemplazo, así el pool no se va achicando en silencio (una excepción en una `Task` que nadie
espera se pierde sin ruido).

**¿Por qué no hace falta un `Lock`?** Todo el estado vive en un solo hilo, y el event loop solo cambia de corrutina en un
`await`. Los métodos de `Registro` son síncronos (sin `await`), así que cada uno es atómico respecto de las demás
corrutinas. Un lock haría falta si hubiera un `await` dentro de una sección crítica, y se evitó a propósito.

**Otras decisiones.** Un único `httpx.AsyncClient` para todo el servicio (reutiliza conexiones) y un semáforo global de
descargas para no agotar file descriptors. El `ProcessPoolExecutor` usa `spawn` en todas las plataformas, con la guarda
`if __name__ == "__main__"`. El volcado se escribe a un `.tmp` y se renombra con `os.replace` (atómico).

## 4. Mediciones

Todas se reproducen con `python mediciones/medir.py` (levanta su propio servidor de prueba con latencia fija de 0,3 s por
respuesta y escribe `mediciones/resultados.md`). Los números son de mi máquina:
AMD Ryzen 5 5500 (6 núcleos / 12 hilos lógicos), 7,7 GB de RAM visibles en WSL2 (Ubuntu en Windows) y Python 3.12.

### 4.1 Concurrencia I/O (20 descargas)

| | Tiempo |
|---|---|
| 20 secuenciales | 6,21 s |
| 20 concurrentes | 0,34 s |
| Speedup | 18,2× |
| 1 tarea `descargar` con 20 URLs vía la API | 0,34 s |

**Interpretación.** Las 20 descargas secuenciales tardan la suma de las esperas (20 × 0,3 s ≈ 6 s). Las concurrentes
tardan aproximadamente lo que la más lenta (0,3 s más un pequeño costo fijo), porque mientras una descarga espera la red,
las otras avanzan en el mismo hilo: el event loop pasa de una a otra cada vez que una llega a un `await`. Por eso el
speedup (18,2×) queda cerca de 20× pero no lo alcanza: crear las conexiones y repartir el trabajo tiene un costo. La
tarea `descargar` hecha a través de la API tarda lo mismo que el `gather` directo, así que el pool y la cola no agregan
una demora apreciable.

### 4.2 Event loop bloqueado

Tarea `hashear` de 30.000.000 iteraciones, con sondeos de `GET /tareas` cada 50 ms durante el hash.

| | Tarea completa | `GET /tareas` máximo | `GET /tareas` mediana | Sondeos que respondieron |
|---|---|---|---|---|
| Sin executor (`--hash-bloqueante true`) | 8,10 s | 8302 ms | 8302 ms | 1 |
| Con executor | 8,46 s | 4 ms | 2,4 ms | 74 |

**Interpretación.** El cálculo tarda prácticamente lo mismo en los dos casos (unos 8 s): el executor no hace más rápido
el hash. Lo que cambia es qué le pasa al resto del servicio. Sin executor, el hash corre dentro del event loop y, como no
tiene ningún `await`, el loop no puede atender nada hasta que termina: el único sondeo que se hizo tardó 8,3 s en
responder, o sea que la API estuvo congelada todo el tiempo que duró el cálculo. Con executor, el hash corre en otro
proceso (otro núcleo, otro intérprete, otro GIL) y el loop queda libre: se pudieron hacer 74 sondeos y el peor tardó 4 ms.
La pequeña diferencia de 0,36 s a favor del caso sin executor es el costo de partir el trabajo en trozos y mandarlos a
otro proceso. Es un precio muy bajo comparado con tener la API caída.

### 4.3 Techo del pool

Tareas `esperar` de 1 s con 50 workers y `--cola-max 20000` (con el valor por defecto, 1000, las tareas que no entran en
la cola reciben `503`). "Ideal" es `ceil(tareas / 50)` segundos.

| Tareas | Tiempo total | Ideal | `GET /tareas` máx | fds | threads | RSS (MB) |
|---|---|---|---|---|---|---|
| 10 | 1,1 s | 1 s | 3 ms | 49 | 3 | 52,1 |
| 50 | 1,1 s | 1 s | 3 ms | 49 | 3 | 52,4 |
| 100 | 2,2 s | 2 s | 3 ms | 47 | 3 | 52,7 |
| 500 | 10,3 s | 10 s | 5 ms | 40 | 3 | 53,8 |
| 1000 | 20,4 s | 20 s | 11 ms | 40 | 3 | 55,9 |
| 3000 | 61,4 s | 60 s | 37 ms | 40 | 3 | 63,0 |
| 10000 | 222,3 s | 200 s | 86 ms | 40 | 3 | 83,6 |

**Interpretación.** Hasta 3000 tareas el tiempo medido acompaña al ideal (menos de 3 % de diferencia): el pool escala
bien. El techo de *throughput* es la cantidad de workers: con 50 workers y tareas de 1 s se terminan 50 por segundo, y lo
que excede de 50 simplemente espera en la cola (por eso 100 tareas tardan 2 s y 1000 tardan 20 s). Recién con 10000
tareas el tiempo se separa del ideal (222 s contra 200 s, un 11 % más) y la latencia de `GET /tareas` sube de 3 ms a
86 ms. Lo que se degrada no es el pool sino el costo de mantener tantas tareas: cada `GET /tareas` arma la representación
de todas las tareas registradas antes de recortar el resultado, así que su costo crece con el tamaño del registro, y la
memoria crece de forma lineal (de 52 MB a 84 MB). Los file descriptors y los threads se mantienen constantes porque las
tareas `esperar` no abren conexiones ni procesos. Para tareas `descargar` el límite sería otro: los file descriptors y
`--max-conexiones`. Además, con la configuración por defecto la cola aguanta 1000 tareas encoladas a la vez y rechaza el
resto con `503`: es lo primero que "se rompe" si llegan 10.000 tareas de golpe, y es intencional (backpressure) para no
quedarse sin memoria.

## 5. Conceptos del curso aplicados

| Parte del código | Concepto | Clase |
|---|---|---|
| Pool de workers que consume de una cola compartida (`workers.py`, `cola.py`) | Productor-consumidor, igual que en la clase 11 pero con corrutinas: acá no hace falta lock porque el loop no interrumpe entre `await` | 11, 18, 20 |
| `asyncio.sleep` en `esperar`; nunca `time.sleep` | Un `time.sleep` en una corrutina congela todo el loop | 18 |
| `hashear` por `run_in_executor` + `ProcessPoolExecutor` | GIL y CPU-bound; procesos en vez de threads; *pickle* de lo que viaja al proceso | 14, 21, 22 |
| Servidor FastAPI sobre uvicorn, `async def` en los endpoints | HTTP, ASGI, métodos y códigos de estado | 19 |
| `httpx.AsyncClient` único y semáforo | I/O asíncrona de red, límite de conexiones | 20 |
| `asyncio.wait_for`, `cancel()`, `CancelledError` y `cancelling()` | Timeouts y cancelación cooperativa | 20, 21 |
| `PriorityQueue(maxsize)` y `503` si se llena | Backpressure | 21 |
| Lifespan y `Servidor.handle_exit` | Señales y apagado ordenado | 6, 21 |
| `Dockerfile`, `docker-compose.yml`, volumen de `datos/`, `stop_grace_period` | Contenedores | 2 |
| `/estadisticas` lee `/proc/self` (fds, threads, RSS) | Mismo enfoque del monitor del TP1 | TP1 |
| Config por flags y variables de entorno | `argparse` | bloque 0 |

## 6. Limitaciones conocidas

- **El estado vive en memoria.** Si el proceso muere sin apagado ordenado (`kill -9`, corte de luz) se pierde todo; el
  volcado JSON solo ocurre en el apagado, y al arrancar solo se *reporta* por log, no se restaura.
- **Un solo proceso y un solo event loop.** Escala hacia arriba en tareas I/O, pero no hay distribución entre máquinas.
- **La cola es finita.** Con más de `--cola-max` tareas encoladas a la vez, el cliente recibe `503` y tiene que reintentar.
- **Sin anti-inanición.** La cola es de prioridades puras: un flujo constante de tareas de prioridad 5 puede dejar
  esperando indefinidamente a las de prioridad 1. Se resolvería con *aging* (subir la prioridad de las que más esperan).
- **El registro nunca se purga y `GET /tareas` es O(n).** Las tareas terminadas quedan en memoria hasta el apagado, y el
  listado arma el diccionario de todas ellas antes de aplicar `limite`, así que con decenas de miles de tareas la latencia
  sube (86 ms con 10000, ver 4.3). Una mejora sería paginar sin construir la lista completa o eliminar las tareas
  terminadas después de un tiempo.
- **Los volcados JSON se acumulan.** Cada apagado crea un `estado_<timestamp>.json` y nunca se borran los anteriores.
- **La cancelación de `hashear` no es instantánea:** el trozo en curso (hasta `chunk_hash` iteraciones) termina antes.
- **Sin autenticación.** Cualquiera con acceso al puerto puede crear y cancelar tareas.
- **`/estadisticas` lee `/proc`**, por lo que `fds_abiertos`, `threads` y `rss_mb` solo funcionan en Linux (en otros
  sistemas el campo `proceso` es `null`).

## 7. Lo que aprendí

Este TP me ayudó a entender de verdad cómo funciona la ejecución concurrente por dentro. Antes tenía la idea de que
"asíncrono" era sinónimo de "más rápido", y las mediciones me mostraron que depende de qué espera la tarea: las descargas
mejoran 18 veces porque casi todo su tiempo es esperar la red, pero el hash no se acelera nada dentro del event loop, y lo
único que cambia al sacarlo a otro proceso es que la API deja de congelarse. Entender la diferencia entre corrutinas
(concurrencia, un solo hilo que va cambiando de tarea en cada `await`), hilos y procesos (paralelismo real, con el GIL de
por medio) fue lo más importante.

Lo que más me costó fue interpretar las mediciones y entender decisiones que al principio parecían detalles: usar una
`PriorityQueue` con un contador para desempatar (FIFO entre tareas de igual prioridad), por qué cada tarea corre en su
propia `Task` para poder cancelarla sin matar al worker, por qué `task_done()` va en un `finally`, y por qué el apagado
tiene que cerrar primero la entrada y recién después esperar y volcar. 

Me gustó volver a usar cosas de las primeras clases (señales, `argparse`, Docker, lectura de `/proc`) y ver que todo lo
que vimos sirve y se conecta. Y me parece muy importante testear: los tests de cancelación, de timeout y de que el hash no
congela el loop me dieron confianza para tocar el código. 