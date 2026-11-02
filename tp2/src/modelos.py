"""Modelos de entrada y salida de la API. Pydantic valida por nosotros (clase 19)."""
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class Estado(StrEnum):
    PENDIENTE = "pendiente"
    EJECUTANDO = "ejecutando"
    COMPLETADA = "completada"
    FALLIDA = "fallida"
    CANCELADA = "cancelada"


TERMINALES = {Estado.COMPLETADA, Estado.FALLIDA, Estado.CANCELADA}


class _Base(BaseModel):
    prioridad: int = Field(default=3, ge=1, le=5, description="1 = más baja, 5 = más alta")
    timeout: float | None = Field(default=None, gt=0, le=3600, description="segundos; por defecto el del servidor")


class NuevaDescargar(_Base):
    tipo: Literal["descargar"]
    urls: list[AnyHttpUrl] = Field(min_length=1, max_length=100)


class NuevaHashear(_Base):
    tipo: Literal["hashear"]
    texto: str = Field(max_length=10_000)
    iteraciones: int = Field(ge=1, le=100_000_000)


class NuevaEsperar(_Base):
    tipo: Literal["esperar"]
    segundos: float = Field(ge=0, le=3600)


# Unión discriminada por `tipo`: cada tipo valida SUS campos y el error dice cuál falta.
TareaNueva = Annotated[NuevaDescargar | NuevaHashear | NuevaEsperar, Field(discriminator="tipo")]

CAMPOS_COMUNES = {"tipo", "prioridad", "timeout"}


class TareaOut(BaseModel):
    id: int
    tipo: str
    estado: Estado
    prioridad: int
    timeout: float
    params: dict[str, Any]
    resultado: Any = None
    error: str | None = None
    creada: float
    iniciada: float | None = None
    terminada: float | None = None
