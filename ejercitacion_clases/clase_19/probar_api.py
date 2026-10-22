"""Prueba los errores del ejercicio 3 contra api.py sin levantar servidor (TestClient)."""
from fastapi.testclient import TestClient

import api

c = TestClient(api.app)


def mostrar(titulo, r):
    detalle = r.json().get("detail")
    print(f"{titulo:34s} -> {r.status_code} {detalle if not isinstance(detalle, list) else detalle[0]['loc'] + [detalle[0]['msg']]}")


mostrar("GET /tareas/abc", c.get("/tareas/abc"))
mostrar("POST tipo=volar", c.post("/tareas", json={"tipo": "volar"}))
mostrar("POST prioridad=99", c.post("/tareas", json={"tipo": "esperar", "prioridad": 99}))
mostrar("GET /tareas/999", c.get("/tareas/999"))

for _ in range(10):
    c.post("/tareas", json={"tipo": "esperar"})
r = c.post("/tareas", json={"tipo": "esperar"})
print(f"{'POST #11 con 10 pendientes':34s} -> {r.status_code} {r.json()['detail']} Retry-After={r.headers['retry-after']}")
print("PATCH:", c.patch("/tareas/1", json={"estado": "completada"}).json())
print("GET /estadisticas:", c.get("/estadisticas").json())
