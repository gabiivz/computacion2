"""Lo que más se evalúa: cancelación limpia, timeouts, loop libre, prioridades y workers que sobreviven a errores."""
import asyncio
import time

import src.tareas as tareas
from tests.conftest import esperar_estado


async def test_cancelar_tarea_en_ejecucion_libera_al_worker(cliente):
    async with cliente(workers=1) as c:
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 30})  # id 1, ocupa al único worker
        await esperar_estado(c.http, 1, {"ejecutando"})
        r = await c.http.delete("/tareas/1")
        assert r.status_code == 200 and r.json()["estado"] == "cancelada"
        # el worker siguió vivo y toma la próxima
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 0.05})
        await esperar_estado(c.http, 2, {"completada"})
        assert (await c.http.delete("/tareas/1")).status_code == 409  # ya estaba cancelada


async def test_cancelar_pendiente_nunca_se_ejecuta(cliente):
    async with cliente(workers=1) as c:
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 0.5})  # 1: ocupa el worker
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 0.5})  # 2: queda pendiente
        r = await c.http.delete("/tareas/2")
        assert r.json()["estado"] == "cancelada"
        await esperar_estado(c.http, 1, {"completada"})
        await asyncio.sleep(0.2)
        t2 = (await c.http.get("/tareas/2")).json()
        assert t2["estado"] == "cancelada" and t2["iniciada"] is None


async def test_timeout_pasa_a_fallida_con_motivo(cliente):
    async with cliente() as c:
        r = await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 10, "timeout": 0.2})
        t = await esperar_estado(c.http, r.json()["id"], {"fallida"})
        assert "timeout" in t["error"]


async def test_hashear_no_congela_el_event_loop(cliente):
    async with cliente(chunk_hash=100_000) as c:
        r = await c.http.post("/tareas", json={"tipo": "hashear", "texto": "x", "iteraciones": 3_000_000})
        await esperar_estado(c.http, r.json()["id"], {"ejecutando"})
        peor = 0.0
        for _ in range(20):  # mientras hashea, el GET tiene que seguir contestando rápido
            t0 = time.perf_counter()
            assert (await c.http.get("/tareas")).status_code == 200
            peor = max(peor, time.perf_counter() - t0)
            await asyncio.sleep(0.02)
        assert peor < 0.15, f"el loop estuvo bloqueado {peor:.3f}s"
        assert (await c.http.get(f"/tareas/{r.json()['id']}")).json()["estado"] == "ejecutando"  # seguía calculando


async def test_cancelar_hashear_en_ejecucion(cliente):
    async with cliente(chunk_hash=50_000) as c:
        r = await c.http.post("/tareas", json={"tipo": "hashear", "texto": "x", "iteraciones": 50_000_000})
        await esperar_estado(c.http, r.json()["id"], {"ejecutando"})
        t0 = time.perf_counter()
        d = await c.http.delete(f"/tareas/{r.json()['id']}")
        assert d.json()["estado"] == "cancelada"
        assert time.perf_counter() - t0 < 1.0  # actúa entre trozos: no espera a las 50 M de iteraciones


async def test_prioridad_mayor_se_ejecuta_primero(cliente):
    async with cliente(workers=1) as c:
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 0.3})  # 1: ocupa el worker
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 0.01, "prioridad": 1})  # 2
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 0.01, "prioridad": 5})  # 3
        t2 = await esperar_estado(c.http, 2, {"completada"})
        t3 = await esperar_estado(c.http, 3, {"completada"})
        assert t3["iniciada"] < t2["iniciada"]


async def test_excepcion_en_una_tarea_no_mata_al_worker(cliente, monkeypatch):
    async def rota(params, ctx):
        raise RuntimeError("bug en la tarea")

    monkeypatch.setitem(tareas.EJECUTORES, "esperar", rota)
    async with cliente(workers=1) as c:
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 1})
        t = await esperar_estado(c.http, 1, {"fallida"})
        assert "RuntimeError" in t["error"]
        monkeypatch.undo()  # el worker sigue vivo: la próxima tarea (ya sana) se ejecuta
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 0.01})
        await esperar_estado(c.http, 2, {"completada"})


async def test_apagado_corta_tareas_que_no_terminan_a_tiempo(cliente):
    async with cliente(apagado_timeout=0.3) as c:
        await c.http.post("/tareas", json={"tipo": "esperar", "segundos": 30})
        await esperar_estado(c.http, 1, {"ejecutando"})
        registro = c.app.state.registro
    t = registro.get(1)  # tras salir del contexto: el lifespan ya hizo el apagado
    assert t.estado.value == "cancelada" and "apagado" in t.error
