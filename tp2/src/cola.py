"""La cola de tareas: asyncio.PriorityQueue acotada (maxsize).

Es una asyncio.Queue y no una queue.Queue: sus get()/put() son corrutinas que ceden el loop en vez de bloquear el hilo,
y no usa locks porque el loop nunca se interrumpe entre awaits. Con maxsize, put_nowait() lanza QueueFull cuando se
llena y la API responde 503: eso es backpressure (clase 21), en vez de crecer sin límite hasta quedarse sin memoria.
"""
import asyncio
import itertools

from .estado import Tarea


class ColaTareas:
    def __init__(self, maxsize: int):
        self._q: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize)
        self._orden = itertools.count()  # desempata: a igual prioridad, FIFO (y nunca se comparan los ids)

    def encolar(self, tarea: Tarea):
        """Lanza asyncio.QueueFull si no hay lugar. Mayor prioridad sale primero (por eso el signo)."""
        self._q.put_nowait((-tarea.prioridad, next(self._orden), tarea.id))

    async def obtener(self) -> int:
        return (await self._q.get())[2]

    def hecha(self):
        self._q.task_done()

    def tamano(self) -> int:
        return self._q.qsize()
