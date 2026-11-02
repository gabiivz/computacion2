"""Endpoints HTTP. Todos son async y NINGUNO espera a que una tarea termine: POST solo encola y responde."""
import asyncio
import os

from fastapi import APIRouter, HTTPException, Query, Request

from .modelos import CAMPOS_COMUNES, TERMINALES, Estado, TareaNueva, TareaOut

router = APIRouter()


@router.post("/tareas", response_model=TareaOut, status_code=201)
async def crear(nueva: TareaNueva, request: Request):
    st = request.app.state
    if st.apagando:
        raise HTTPException(503, "El servicio se está apagando", headers={"Retry-After": "30"})
    params = nueva.model_dump(mode="json", exclude=CAMPOS_COMUNES)
    tarea = st.registro.crear(nueva.tipo, params, nueva.prioridad, nueva.timeout or st.cfg.timeout_default)
    try:
        st.cola.encolar(tarea)
    except asyncio.QueueFull:
        st.registro.descartar(tarea.id)  # no dejar una tarea fantasma que nadie va a ejecutar
        raise HTTPException(503, "Cola llena, reintentá más tarde", headers={"Retry-After": "5"})
    return tarea.a_dict()


@router.get("/tareas", response_model=list[TareaOut])
async def listar(request: Request, estado: Estado | None = None, limite: int = Query(100, ge=1, le=1000)):
    return [t.a_dict() for t in request.app.state.registro.listar(estado)][:limite]


def _o_404(request: Request, id: int):
    tarea = request.app.state.registro.get(id)
    if tarea is None:
        raise HTTPException(404, f"La tarea {id} no existe")
    return tarea


@router.get("/tareas/{id}", response_model=TareaOut)
async def obtener(id: int, request: Request):
    return _o_404(request, id).a_dict()


@router.delete("/tareas/{id}", response_model=TareaOut)
async def cancelar(id: int, request: Request):
    tarea = _o_404(request, id)
    if tarea.estado in TERMINALES:
        raise HTTPException(409, f"La tarea ya está {tarea.estado.value}")
    await request.app.state.pool.cancelar(tarea)
    return tarea.a_dict()


def _proceso() -> dict | None:
    """Fds, threads y RSS leídos de /proc, como el monitor del TP1 (solo Linux). Útil para la medición 3."""
    try:
        with open("/proc/self/status") as f:
            campos = dict(l.split(":", 1) for l in f if ":" in l)
        return {"fds_abiertos": len(os.listdir("/proc/self/fd")), "threads": int(campos["Threads"]),
                "rss_mb": round(int(campos["VmRSS"].split()[0]) / 1024, 1)}
    except (OSError, KeyError):
        return None


@router.get("/estadisticas")
async def estadisticas(request: Request):
    st = request.app.state
    por_estado = st.registro.por_estado()
    return {"total": sum(por_estado.values()), "por_estado": por_estado,
            "cola": {"tamano": st.cola.tamano(), "maximo": st.cfg.cola_max},
            "workers": {"total": st.cfg.workers, "ocupados": len(st.pool.ocupados)},
            "tiempos_promedio": st.registro.tiempos_promedio(), "proceso": _proceso()}
