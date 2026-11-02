"""Configuración del servicio.

Cada opción se puede pasar por línea de comandos (argparse, bloque 0) y su valor por defecto sale de una
variable de entorno con el mismo nombre en mayúsculas (docker-compose `environment:`, clase 2). Prioridad:
argumento > variable de entorno > valor por defecto del código.
"""
import argparse
import os
from dataclasses import dataclass, fields


@dataclass
class Config:
    host: str = "0.0.0.0"
    puerto: int = 8000
    workers: int = 4  # corrutinas consumidoras de la cola
    cola_max: int = 1000  # capacidad de la cola: más allá se responde 503 (backpressure)
    timeout_default: float = 30.0  # segundos por tarea si el pedido no trae uno
    procesos: int = max(1, os.cpu_count() or 1)  # procesos del ProcessPoolExecutor (CPU-bound)
    chunk_hash: int = 200_000  # iteraciones de hash por viaje al executor (granularidad de cancelación)
    max_conexiones: int = 100  # tope de descargas simultáneas en todo el servicio
    apagado_timeout: float = 10.0  # espera máxima por las tareas en curso al apagar
    datos_dir: str = "datos"  # donde se vuelca estado_<timestamp>.json
    hash_bloqueante: bool = False  # SOLO para la medición 2: hashea en el loop, sin executor
    log_level: str = "INFO"


def _bool(valor):
    return str(valor).lower() in ("1", "true", "si", "sí", "yes")


def cargar(argv=None) -> Config:
    parser = argparse.ArgumentParser(description="Plataforma de tareas distribuidas (TP2 Computación II)")
    base = Config()
    for f in fields(Config):
        nombre = f.name
        tipo = _bool if f.type is bool else f.type  # int, float o str: se usa para convertir env y argv
        defecto = os.environ.get(nombre.upper(), getattr(base, nombre))
        parser.add_argument(f"--{nombre.replace('_', '-')}", dest=nombre, type=tipo, default=tipo(defecto),
                            help=f"(env {nombre.upper()}, por defecto {getattr(base, nombre)})")
    return Config(**vars(parser.parse_args(argv)))
