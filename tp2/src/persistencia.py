"""Volcado del estado a JSON al apagar, y reporte del volcado previo al arrancar."""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from .estado import Registro

log = logging.getLogger("tareas.persistencia")


def volcar(registro: Registro, directorio: str) -> Path:
    d = Path(directorio)
    d.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now()
    ruta = d / f"estado_{ahora.strftime('%Y%m%d_%H%M%S')}.json"
    datos = {"volcado": ahora.isoformat(timespec="seconds"), "por_estado": registro.por_estado(),
             "tareas": [t.a_dict() for t in registro.tareas.values()]}
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(tmp, ruta)  # atómico: nunca queda un JSON a medio escribir si algo falla en el medio
    return ruta


def reportar_previo(directorio: str):
    previos = sorted(Path(directorio).glob("estado_*.json"))
    if not previos:
        log.info("no hay volcado previo en %s", directorio)
        return
    try:
        datos = json.loads(previos[-1].read_text(encoding="utf-8"))
        log.info("volcado previo encontrado: %s (%d tareas; %s)", previos[-1].name, len(datos["tareas"]),
                 datos["por_estado"])
    except (OSError, ValueError, KeyError) as e:
        log.warning("volcado previo ilegible %s: %s", previos[-1].name, e)
