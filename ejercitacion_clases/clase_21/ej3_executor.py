"""Clase 21 - Ej 3 (obligatorio): sacar el trabajo CPU-bound del event loop.

Mide el "atraso del loop": cada 10 ms pedimos dormir 10 ms y vemos cuánto más tardó en volver el control.
Si el loop está libre el atraso es ~0; si alguien lo bloquea, aparece completo.
"""
import asyncio
import hashlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

ITER = 1_500_000


def ignorar(x):
    return None  # función de módulo (picklable) que solo recibe el argumento


def hashear(n=ITER, texto="hola"):
    h = texto.encode()
    for _ in range(n):
        h = hashlib.sha256(h).digest()
    return h.hex()[:12]


async def medidor(parar, atrasos):
    while not parar.is_set():
        t0 = time.perf_counter()
        await asyncio.sleep(0.01)
        atrasos.append(time.perf_counter() - t0 - 0.01)


async def con_medicion(nombre, trabajo):
    parar, atrasos = asyncio.Event(), []
    m = asyncio.create_task(medidor(parar, atrasos))
    await asyncio.sleep(0.05)
    t0 = time.perf_counter()
    await trabajo()
    total = time.perf_counter() - t0
    parar.set()
    await m
    print(f"{nombre:28s} trabajo={total:5.2f}s  peor atraso del loop={max(atrasos) * 1000:7.0f} ms")


async def parte_a():
    loop = asyncio.get_running_loop()
    pool_p, pool_t = ProcessPoolExecutor(2), ThreadPoolExecutor(2)

    async def sin_executor():
        hashear()  # bloquea el loop: nadie más corre mientras tanto

    async def con_threads():
        await loop.run_in_executor(pool_t, hashear)

    async def con_procesos():
        await loop.run_in_executor(pool_p, hashear)

    await loop.run_in_executor(pool_p, hashear, 10)  # calienta el pool (arranque de procesos)
    await con_medicion("sin executor", sin_executor)
    await con_medicion("ThreadPoolExecutor", con_threads)
    await con_medicion("ProcessPoolExecutor", con_procesos)
    return pool_p, pool_t


async def parte_b(pool_p, pool_t):
    loop = asyncio.get_running_loop()
    for nombre, pool in (("threads", pool_t), ("procesos", pool_p)):
        for n_tareas in (1, 4):
            t0 = time.perf_counter()
            await asyncio.gather(*(loop.run_in_executor(pool, hashear, ITER // 2) for _ in range(n_tareas)))
            print(f"CPU-bound x{n_tareas} con {nombre:8s} {time.perf_counter() - t0:5.2f}s")
    for nombre, pool in (("threads", pool_t), ("procesos", pool_p)):
        t0 = time.perf_counter()
        await asyncio.gather(*(loop.run_in_executor(pool, time.sleep, 0.5) for _ in range(4)))
        print(f"I/O-bound (sleep 0.5) x4 con {nombre:8s} {time.perf_counter() - t0:5.2f}s")

    # Parte C
    try:
        await loop.run_in_executor(pool_p, lambda: 1)
    except Exception as e:
        print(f"lambda al ProcessPool -> {type(e).__name__}: {str(e)[:60]}")
    grande = list(range(1_000_000))
    for nombre, arg in (("un número", 5), ("lista de 1M", grande)):
        t0 = time.perf_counter()
        await loop.run_in_executor(pool_p, ignorar, arg)
        print(f"pasar {nombre:12s} al proceso: {(time.perf_counter() - t0) * 1000:7.1f} ms (pickle ida y vuelta)")
    t0 = time.perf_counter()
    with ProcessPoolExecutor(2) as nuevo:
        await loop.run_in_executor(nuevo, hashear, 10)
    print(f"crear un pool nuevo + una tarea mínima: {(time.perf_counter() - t0) * 1000:.0f} ms")


async def main():
    pool_p, pool_t = await parte_a()
    await parte_b(pool_p, pool_t)
    pool_p.shutdown()
    pool_t.shutdown()


if __name__ == "__main__":  # imprescindible con ProcessPoolExecutor en spawn (macOS/Windows)
    asyncio.run(main())
    sys.exit(0)
