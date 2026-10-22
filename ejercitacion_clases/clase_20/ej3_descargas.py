"""Clase 20 - Ej 3 (obligatorio): concurrencia de clientes, acotar con Semaphore y manejar fallos.

Levanta un servidor HTTP local lento (en otro hilo, con su propio event loop) para medir sin depender de internet.
"""
import asyncio
import threading
import time

import httpx

LATENCIA = 0.3  # cada respuesta del servidor local tarda 0.3 s


# ---------- servidor local (asyncio puro, clase 20) ----------
async def _atender(reader, writer):
    try:
        while True:  # keep-alive: varios pedidos por la misma conexión
            await reader.readuntil(b"\r\n\r\n")
            await asyncio.sleep(LATENCIA)
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: keep-alive\r\n\r\nok")
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionError):
        pass  # el cliente cerró
    finally:
        writer.close()


def levantar_servidor():
    listo = threading.Event()
    info = {}

    def correr():
        async def main():
            srv = await asyncio.start_server(_atender, "127.0.0.1", 0, backlog=1024)
            info["puerto"] = srv.sockets[0].getsockname()[1]
            listo.set()
            await srv.serve_forever()

        asyncio.run(main())

    threading.Thread(target=correr, daemon=True).start()
    listo.wait()
    return info["puerto"]


# ---------- clientes ----------
async def bajar(cliente, url):
    r = await cliente.get(url)
    return url, r.status_code, len(r.content)


async def medir(nombre, coro):
    t0 = time.perf_counter()
    res = await coro
    print(f"{nombre:42s} {time.perf_counter() - t0:6.2f}s")
    return res


async def main():
    puerto = levantar_servidor()
    url = f"http://127.0.0.1:{puerto}/"
    urls = [url] * 10
    # El cliente se crea UNA vez: reutiliza conexiones (keep-alive) y comparte el pool
    async with httpx.AsyncClient(timeout=10, limits=httpx.Limits(max_connections=500)) as c:
        async def secuencial():
            return [await bajar(c, u) for u in urls]

        await medir("10 secuenciales (for + await)", secuencial())
        await medir("10 concurrentes (gather)", asyncio.gather(*(bajar(c, u) for u in urls)))

        sem = asyncio.Semaphore(3)

        async def acotada(u):
            async with sem:
                return await bajar(c, u)

        await medir("10 con Semaphore(3)", asyncio.gather(*(acotada(u) for u in urls)))

        # Parte D: fallos. Una URL inválida entre las buenas.
        mala = "http://127.0.0.1:1/"  # puerto cerrado
        mezcla = urls[:3] + [mala] + urls[3:6]
        try:
            await asyncio.gather(*(bajar(c, u) for u in mezcla))
        except Exception as e:
            print(f"gather normal -> lanza {type(e).__name__}: se pierde el resultado de las que sí andaban")
        res = await asyncio.gather(*(bajar(c, u) for u in mezcla), return_exceptions=True)
        print("gather(return_exceptions=True) ->", [type(r).__name__ if isinstance(r, Exception) else r[1] for r in res])

    # 200 conexiones concurrentes sin semáforo: ok acá porque ulimit -n es alto; con ulimit 1024 daría "Too many open files"
    async with httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=500)) as c:
        await medir("200 concurrentes sin semáforo", asyncio.gather(*(bajar(c, url) for _ in range(200))))

    # timeout: 0.1 < latencia 0.3 -> todas se cancelan
    async with httpx.AsyncClient() as c:
        res = await asyncio.gather(
            *(asyncio.wait_for(bajar(c, url), timeout=0.1) for _ in range(5)), return_exceptions=True)
        print("wait_for(0.1s) ->", [type(r).__name__ for r in res])

    # requests dentro de una corrutina bloquea el loop
    try:
        import requests

        async def con_requests(u):
            return requests.get(u)  # llamada bloqueante dentro de una corrutina: congela el loop entero

        await medir("10 'concurrentes' con requests (bloquea)", asyncio.gather(*(con_requests(u) for u in urls)))
    except ImportError:
        print("(requests no instalado: se omite la prueba de bloqueo)")


if __name__ == "__main__":
    asyncio.run(main())
