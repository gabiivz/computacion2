## Medición 1 — Concurrencia I/O: 20 descargas
- 20 secuenciales (cliente): 6.21 s
- 20 concurrentes (cliente, gather): 0.34 s  → speedup 18.2x
- 1 tarea `descargar` con 20 URLs vía la API: 0.34 s  → speedup 18.2x (ideal ≈ 0.3 s)

## Medición 2 — Event loop bloqueado (hashear 30,000,000 iteraciones)
- SIN executor (hash en el loop): tarea completa en 8.10 s · GET /tareas durante el hash: máximo 8302 ms, mediana 8302.1 ms (1 sondeos)
- CON executor: tarea completa en 8.46 s · GET /tareas durante el hash: máximo 4 ms, mediana 2.4 ms (74 sondeos)

## Medición 3 — Techo del pool (tareas `esperar` de 1 s con 50 workers)
| tareas simultáneas | tiempo total | ideal | latencia GET /tareas (máx) | fds | threads | RSS MB |
|---|---|---|---|---|---|---|
| 10 | 1.1 s | 1 s | 3 ms | 49 | 3 | 52.1 |
| 50 | 1.1 s | 1 s | 3 ms | 49 | 3 | 52.4 |
| 100 | 2.2 s | 2 s | 3 ms | 47 | 3 | 52.7 |
| 500 | 10.3 s | 10 s | 5 ms | 40 | 3 | 53.8 |
| 1000 | 20.4 s | 20 s | 11 ms | 40 | 3 | 55.9 |
| 3000 | 61.4 s | 60 s | 37 ms | 40 | 3 | 63.0 |
| 10000 | 222.3 s | 200 s | 86 ms | 40 | 3 | 83.6 |

