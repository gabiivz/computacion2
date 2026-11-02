import asyncio
import time

import httpx


async def ejecutar(params, ctx):
    """Descarga todas las URLs a la vez y devuelve estado, tamaño y tiempo de cada una.

    Una URL que falla no tira abajo a las demás (decisión de la clase 20, ej. 3.12): el error queda en SU entrada.
    El semáforo es global al servicio para no agotar file descriptors si llegan muchas tareas a la vez.
    """

    async def una(url):
        async with ctx.sem_descargas:
            t0 = time.perf_counter()
            try:
                r = await ctx.http.get(url)
                return {"url": url, "estado": r.status_code, "bytes": len(r.content),
                        "ms": round((time.perf_counter() - t0) * 1000, 1)}
            except httpx.HTTPError as e:  # CancelledError NO es HTTPError: la cancelación sigue de largo
                return {"url": url, "error": f"{type(e).__name__}: {e}",
                        "ms": round((time.perf_counter() - t0) * 1000, 1)}

    # Si cancelan la tarea, gather cancela a todas las hijas y httpx cierra sus conexiones.
    return await asyncio.gather(*(una(str(u)) for u in params["urls"]))
