"""Armado de la aplicación: el lifespan crea y cierra TODOS los recursos (cola, workers, executor, cliente HTTP)."""
import asyncio
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from . import persistencia
from .api import router
from .cola import ColaTareas
from .config import Config
from .estado import Registro
from .tareas import Contexto
from .tareas.hashear import calentar
from .workers import Pool

log = logging.getLogger("tareas.app")


def crear_app(cfg: Config, transporte_http: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    """`transporte_http` permite inyectar un transporte falso en los tests (sin tocar la red)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()
        registro, cola = Registro(), ColaTareas(cfg.cola_max)
        # spawn en todas las plataformas: mismo comportamiento en Linux, macOS y Windows, y sin fork() con hilos vivos.
        procesos = ProcessPoolExecutor(cfg.procesos, mp_context=multiprocessing.get_context("spawn"))
        limites = httpx.Limits(max_connections=cfg.max_conexiones)
        # UN cliente para todo el servicio: reutiliza conexiones (keep-alive) y comparte el pool de sockets.
        async with httpx.AsyncClient(timeout=10, limits=limites, transport=transporte_http) as http:
            ctx = Contexto(http, procesos, asyncio.Semaphore(cfg.max_conexiones), cfg.chunk_hash, cfg.hash_bloqueante)
            pool = Pool(cola, registro, ctx, cfg.workers)
            app.state.cfg, app.state.registro, app.state.cola, app.state.pool = cfg, registro, cola, pool

            persistencia.reportar_previo(cfg.datos_dir)
            if cfg.hash_bloqueante:
                log.warning("hash_bloqueante=True: modo de medición, el loop se bloquea con hashear")
            await asyncio.gather(*(loop.run_in_executor(procesos, calentar) for _ in range(cfg.procesos)))
            pool.iniciar()
            log.info("listo: %d workers, %d procesos, cola máx. %d", cfg.workers, cfg.procesos, cfg.cola_max)

            yield  # ---- el servicio atiende ----

            # ---- apagado ordenado ----
            app.state.apagando = True  # 1. no aceptar tareas nuevas (si no lo bajó ya el handler de la señal)
            await pool.detener(cfg.apagado_timeout)  # 2. esperar (con límite) a las que están en curso
            log.info("estado volcado en %s", persistencia.volcar(registro, cfg.datos_dir))  # 3. volcar a JSON
        procesos.shutdown(wait=True, cancel_futures=True)

    app = FastAPI(title="Plataforma de tareas distribuidas", description="TP2 Computación II", lifespan=lifespan)
    app.state.apagando = False
    app.include_router(router)
    return app
