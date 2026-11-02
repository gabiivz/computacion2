import asyncio
import hashlib
import time


def paso(estado: bytes, n: int) -> bytes:
    """n vueltas de SHA-256 sobre el resultado anterior. Función de módulo: tiene que ser picklable para viajar al proceso."""
    for _ in range(n):
        estado = hashlib.sha256(estado).digest()
    return estado


def calentar():
    """Se usa al arrancar para forzar que nazcan todos los procesos del pool (si no, nacen en la primera tarea)."""
    time.sleep(0.1)


async def ejecutar(params, ctx):
    """Hash iterado, CPU-bound. Un SHA-256 iterado en el loop lo congelaría, así que se hace en otro proceso.

    Se divide en trozos de `chunk_hash` iteraciones, un viaje al executor por trozo. Un job que ya corre en un proceso
    NO se puede interrumpir (ni con cancel() ni con timeout); troceando, la cancelación y el timeout actúan entre
    trozos y el proceso nunca queda calculando para nadie más de un trozo.
    """
    estado = params["texto"].encode()
    restantes = params["iteraciones"]

    if ctx.hash_bloqueante:  # medición 2 del TP2: lo que NO hay que hacer
        estado = paso(estado, restantes)
        return {"iteraciones": params["iteraciones"], "sha256": estado.hex()}

    loop = asyncio.get_running_loop()
    while restantes > 0:
        n = min(ctx.chunk_hash, restantes)
        estado = await loop.run_in_executor(ctx.procesos, paso, estado, n)  # acá cede el loop y se puede cancelar
        restantes -= n
    return {"iteraciones": params["iteraciones"], "sha256": estado.hex()}
