"""Clase 19 - Ej 3 (obligatorio): esqueleto de la API del TP2 (datos en memoria, sin concurrencia todavía).

Uso: pip install fastapi uvicorn httpx && python3 api.py   ->  http://localhost:8000/docs
"""
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Tareas", description="Clase 19: HTTP + FastAPI")

Estado = Literal["pendiente", "ejecutando", "completada", "fallida", "cancelada"]
MAX_PENDIENTES = 10

tareas: dict[int, dict] = {}
proximo_id = 0


class TareaNueva(BaseModel):
    tipo: Literal["descargar", "hashear", "esperar"]
    prioridad: int = Field(default=1, ge=1, le=5, description="1 = más baja, 5 = más alta")


class Tarea(TareaNueva):
    id: int
    estado: Estado = "pendiente"


class TareaPatch(BaseModel):
    """PATCH: todos los campos opcionales; solo se cambia lo que viene."""
    estado: Estado | None = None


@app.get("/tareas", response_model=list[Tarea])
async def listar(estado: Estado | None = Query(default=None), limite: int = Query(default=10, ge=1, le=100)):
    items = [t for t in tareas.values() if estado is None or t["estado"] == estado]
    return items[:limite]


@app.post("/tareas", response_model=Tarea, status_code=201)
async def crear(nueva: TareaNueva):
    global proximo_id
    pendientes = sum(1 for t in tareas.values() if t["estado"] == "pendiente")
    if pendientes >= MAX_PENDIENTES:
        # 503 + Retry-After: el servidor está saturado (no es culpa del cliente ni un límite por cliente, que sería 429)
        raise HTTPException(status_code=503, detail="Demasiadas tareas pendientes", headers={"Retry-After": "5"})
    proximo_id += 1
    tareas[proximo_id] = {"id": proximo_id, **nueva.model_dump(), "estado": "pendiente"}
    return tareas[proximo_id]


@app.get("/tareas/{id}", response_model=Tarea)
async def obtener(id: int):
    if id not in tareas:
        raise HTTPException(status_code=404, detail=f"Tarea {id} no existe")
    return tareas[id]


@app.patch("/tareas/{id}", response_model=Tarea)
async def modificar(id: int, cambios: TareaPatch):
    if id not in tareas:
        raise HTTPException(status_code=404, detail=f"Tarea {id} no existe")
    tareas[id].update(cambios.model_dump(exclude_none=True))
    return tareas[id]


@app.get("/estadisticas")
async def estadisticas():
    por_estado = {e: 0 for e in Estado.__args__}
    for t in tareas.values():
        por_estado[t["estado"]] += 1
    return {"total": len(tareas), "por_estado": por_estado}


if __name__ == "__main__":  # la guarda también es necesaria cuando haya ProcessPoolExecutor (spawn en macOS/Windows)
    uvicorn.run(app, host="0.0.0.0", port=8000)
