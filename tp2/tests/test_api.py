"""Funcionalidad básica de la API: respuesta inmediata, validación, errores y los tres tipos de tarea."""
import json
import time
from pathlib import Path

import httpx

from tests.conftest import esperar_estado


async def test_post_responde_inmediato_y_la_tarea_se_completa(cliente):
    async with cliente() as c:
        t0 = time.perf_counter()
        r = await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 0.3})
        assert time.perf_counter() - t0 < 0.1  # no espera a que la tarea termine
        assert r.status_code == 201 and r.json()["estado"] == "pendiente"
        final = await esperar_estado(c.http, r.json()["id"], {"completada"})
        assert final["resultado"] == {"esperado_s": 0.3}


async def test_validacion_y_404(cliente):
    async with cliente() as c:
        assert (await c.http.post("/tareas", json={"tipo": "volar"})).status_code == 422
        assert (await c.http.post("/tareas", json={"tipo": "esperar"})).status_code == 422  # falta `segundos`
        assert (await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 1, "prioridad": 9})).status_code == 422
        assert (await c.http.get("/tareas/abc")).status_code == 422
        assert (await c.http.get("/tareas/999")).status_code == 404
        assert (await c.http.delete("/tareas/999")).status_code == 404


async def test_hashear_resultado_correcto(cliente):
    import hashlib
    esperado = b"hola"
    for _ in range(250_000):  # más que un chunk (100 000): ejercita el troceado
        esperado = hashlib.sha256(esperado).digest()
    async with cliente() as c:
        r = await c.http.post("/tareas", json={"tipo": "hashear", "texto": "hola", "iteraciones": 250_000})
        t = await esperar_estado(c.http, r.json()["id"], {"completada"})
        assert t["resultado"]["sha256"] == esperado.hex()


async def test_descargar_con_una_url_caida(cliente):
    def respuesta(request: httpx.Request):
        if "caida" in str(request.url):
            raise httpx.ConnectError("sin conexión")
        return httpx.Response(200, content=b"x" * 10)

    async with cliente(transporte_http=httpx.MockTransport(respuesta)) as c:
        urls = ["http://ok.test/a", "http://caida.test/b", "http://ok.test/c"]
        r = await c.http.post("/tareas", json={"tipo": "descargar", "urls": urls})
        res = (await esperar_estado(c.http, r.json()["id"], {"completada"}))["resultado"]
        assert [x.get("estado") for x in res] == [200, None, 200]  # la caída no pierde a las otras
        assert "ConnectError" in res[1]["error"] and res[0]["bytes"] == 10


async def test_cola_llena_devuelve_503(cliente):
    async with cliente(workers=1, cola_max=1) as c:
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 5})  # ocupa al único worker
        await esperar_estado(c.http, 1, {"ejecutando"})
        assert (await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 5})).status_code == 201  # llena la cola
        r = await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 5})
        assert r.status_code == 503 and r.headers["retry-after"]
        assert len((await c.http.get("/tareas")).json()) == 2  # la rechazada no quedó registrada


async def test_estadisticas(cliente):
    async with cliente() as c:
        r = await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 0.05})
        await esperar_estado(c.http, r.json()["id"], {"completada"})
        s = (await c.http.get("/estadisticas")).json()
        assert s["por_estado"]["completada"] == 1 and s["workers"]["total"] == 2 and "esperar" in s["tiempos_promedio"]


async def test_apagado_vuelca_estado_y_el_siguiente_arranque_lo_reporta(cliente, tmp_path, caplog):
    async with cliente() as c:
        r = await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 0.05})
        await esperar_estado(c.http, r.json()["id"], {"completada"})
    volcados = list(Path(tmp_path).glob("estado_*.json"))
    assert len(volcados) == 1
    assert json.loads(volcados[0].read_text())["tareas"][0]["estado"] == "completada"

    with caplog.at_level("INFO"):
        async with cliente():
            pass
    assert any("volcado previo encontrado" in m for m in caplog.messages)
