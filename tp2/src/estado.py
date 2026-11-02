"""Estado en memoria: el registro de tareas.

No hay Lock a propósito: todo corre en UN hilo (el event loop) y el loop solo cambia de corrutina en un `await`.
Cada método de acá es síncrono (no tiene await), así que es atómico respecto de las demás corrutinas (clase 20).
En el TP1 los analizadores eran procesos distintos y sí necesitaban cuidar quién escribía cada clave.
"""
import asyncio
import itertools
import time
from dataclasses import dataclass, field
from typing import Any

from .modelos import TERMINALES, Estado


@dataclass
class Tarea:
    id: int
    tipo: str
    params: dict
    prioridad: int
    timeout: float
    estado: Estado = Estado.PENDIENTE
    resultado: Any = None
    error: str | None = None
    creada: float = field(default_factory=time.time)
    iniciada: float | None = None
    terminada: float | None = None
    handle: asyncio.Task | None = field(default=None, repr=False)  # la corrutina en ejecución (para cancelarla)
    fin: asyncio.Event = field(default_factory=asyncio.Event, repr=False)  # se activa al llegar a un estado final

    def a_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("id", "tipo", "estado", "prioridad", "timeout", "params", "resultado",
                                              "error", "creada", "iniciada", "terminada")}

    def terminar(self, estado: Estado, error: str | None = None):
        self.estado, self.error, self.terminada, self.handle = estado, error, time.time(), None
        self.fin.set()


class Registro:
    def __init__(self):
        self.tareas: dict[int, Tarea] = {}
        self._ids = itertools.count(1)

    def crear(self, tipo, params, prioridad, timeout) -> Tarea:
        t = Tarea(next(self._ids), tipo, params, prioridad, timeout)
        self.tareas[t.id] = t
        return t

    def descartar(self, id: int):
        self.tareas.pop(id, None)

    def get(self, id: int) -> Tarea | None:
        return self.tareas.get(id)

    def listar(self, estado: Estado | None = None) -> list[Tarea]:
        return [t for t in self.tareas.values() if estado is None or t.estado == estado]

    def por_estado(self) -> dict[str, int]:
        cuenta = {e.value: 0 for e in Estado}
        for t in self.tareas.values():
            cuenta[t.estado.value] += 1
        return cuenta

    def tiempos_promedio(self) -> dict[str, dict[str, float]]:
        """Espera en cola y ejecución promedio, por tipo, sobre las tareas que llegaron a ejecutarse y terminar."""
        acum: dict[str, list] = {}
        for t in self.tareas.values():
            if t.estado in TERMINALES and t.iniciada and t.terminada:
                acum.setdefault(t.tipo, []).append((t.iniciada - t.creada, t.terminada - t.iniciada))
        return {tipo: {"espera_s": round(sum(a for a, _ in v) / len(v), 4),
                       "ejecucion_s": round(sum(b for _, b in v) / len(v), 4), "n": len(v)}
                for tipo, v in acum.items()}
