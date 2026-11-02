import asyncio
import time

import httpx
import pytest

from src.app import crear_app
from src.config import Config


def hacer_cliente(tmp_path, transporte_http=None, **cfg):
    """Devuelve un context manager asíncrono que levanta la app con su lifespan y entrega un cliente HTTP."""
    base = dict(workers=2, procesos=2, datos_dir=str(tmp_path), apagado_timeout=2.0, chunk_hash=100_000)
    app = crear_app(Config(**{**base, **cfg}), transporte_http)

    class Ctx:
        async def __aenter__(self):
            self.lifespan = app.router.lifespan_context(app)
            await self.lifespan.__aenter__()
            self.app = app
            self.http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
            return self

        async def __aexit__(self, *exc):
            await self.http.aclose()
            await self.lifespan.__aexit__(*exc)

    return Ctx()


@pytest.fixture
def cliente(tmp_path):
    return lambda **cfg: hacer_cliente(tmp_path, **cfg)


async def esperar_estado(http, id, estados, limite=10.0):
    """Consulta hasta que la tarea llegue a alguno de `estados`; devuelve el JSON."""
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        t = (await http.get(f"/tareas/{id}")).json()
        if t["estado"] in estados:
            return t
        await asyncio.sleep(0.02)
    raise AssertionError(f"la tarea {id} no llegó a {estados}; último estado: {t['estado']}")
