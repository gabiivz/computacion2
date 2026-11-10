# Dudas — TP2

- **`wait_for` y `cancelling()`.** Para distinguir "cancelaron la tarea" de "cancelaron al worker" usé `asyncio.current_task().cancelling()` (Python 3.11+). ¿Hay una forma más simple de separar los dos casos?
- **Tareas canceladas en la cola.** Siguen ocupando un lugar hasta que un worker las saca. ¿Vale la pena una cola propia que permita borrar, o alcanza con documentarlo?
- **Trozos de `hashear`.** `chunk_hash` es un compromiso entre granularidad de cancelación y costo de ida y vuelta al proceso (pickle). ¿Cómo se elige bien el valor? Se podría medir.
- **Inanición con prioridades.** ¿Envejecimiento (subir la prioridad con el tiempo de espera) o cuota por prioridad? Pendiente de decidir si hacerlo.
