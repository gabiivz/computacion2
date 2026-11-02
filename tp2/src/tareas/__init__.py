"""Los tipos de tarea. Cada uno es una corrutina `ejecutar(params, ctx)` que devuelve el resultado."""
import asyncio
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import httpx

from . import descargar, esperar, hashear


@dataclass
class Contexto:
    """Recursos compartidos que reciben las tareas. Se crean UNA vez en el lifespan y se cierran al apagar."""
    http: httpx.AsyncClient
    procesos: ProcessPoolExecutor
    sem_descargas: asyncio.Semaphore
    chunk_hash: int
    hash_bloqueante: bool = False


EJECUTORES = {
    "descargar": descargar.ejecutar,  # I/O-bound: concurrencia asíncrona real
    "hashear": hashear.ejecutar,  # CPU-bound: al ProcessPoolExecutor
    "esperar": esperar.ejecutar,  # I/O simulado: cancelación y timeouts
}
