import select
import json
import signal
from datetime import datetime
from senales import configurar_senales

import multiprocessing
import time
import os

from recolector import recolector_worker
from analizadores.resumen import resumen_worker
from analizadores.fds import fds_worker  
from analizadores.memoria import memoria_worker
from analizadores.senales import senales_worker
from analizadores.threads import threads_worker
from analizadores.scheduling import scheduling_worker
from analizadores.sistema import sistema_worker
from display import display_worker

DEFAULTS_INTERVALOS = {
    "resumen": 2.0, "memoria": 3.0, "fds": 5.0, "threads": 2.0,
    "senales": 10.0, "scheduling": 10.0, "sistema": 2.0
}

def cargar_config_intervalos():
    try:
        with open("/app/config.json", "r") as f:
            data = json.load(f)
            intervalos = data.get("intervalos", {})
            return {**DEFAULTS_INTERVALOS, **intervalos}
    except Exception:
        return dict(DEFAULTS_INTERVALOS)


def cargar_filtro_default():
    """Lee el filtro por defecto desde config.json. Si no está definido
    o el archivo es inválido, devuelve 'sin filtro'."""
    try:
        with open("/app/config.json", "r") as f:
            data = json.load(f)
            filtro = data.get("filtro_default", {})
            return {
                "tipo": filtro.get("tipo", ""),
                "texto": filtro.get("texto", "")
            }
    except Exception:
        return {"tipo": "", "texto": ""}


def main():
    with multiprocessing.Manager() as manager:
        snapshot = manager.dict({
            "resumen": manager.dict(),
        })

        config_inicial = cargar_config_intervalos()

        intervalo_resumen    = multiprocessing.Value('d', config_inicial["resumen"])
        intervalo_memoria    = multiprocessing.Value('d', config_inicial["memoria"])
        intervalo_fds        = multiprocessing.Value('d', config_inicial["fds"])
        intervalo_threads    = multiprocessing.Value('d', config_inicial["threads"])
        intervalo_senales    = multiprocessing.Value('d', config_inicial["senales"])
        intervalo_scheduling = multiprocessing.Value('d', config_inicial["scheduling"])
        intervalo_sistema    = multiprocessing.Value('d', config_inicial["sistema"])

        verbose_flag = multiprocessing.Value('b', 0)
        seguir_corriendo = multiprocessing.Value('b', 1)

        intervalos_por_nombre = {
            "resumen": intervalo_resumen,
            "memoria": intervalo_memoria,
            "fds": intervalo_fds,
            "threads": intervalo_threads,
            "senales": intervalo_senales,
            "scheduling": intervalo_scheduling,
            "sistema": intervalo_sistema,
        }

        snapshot['config_filtro'] = cargar_filtro_default()
        snapshot['config_revision'] = 0

        p_recolector = multiprocessing.Process(target=recolector_worker, args=(snapshot, seguir_corriendo))
        p_resumen = multiprocessing.Process(target=resumen_worker, args=(snapshot, intervalo_resumen, seguir_corriendo))
        p_fds = multiprocessing.Process(target=fds_worker, args=(snapshot, intervalo_fds, seguir_corriendo))
        p_memoria = multiprocessing.Process(target=memoria_worker, args=(snapshot, intervalo_memoria, seguir_corriendo))
        p_senales = multiprocessing.Process(target=senales_worker, args=(snapshot, intervalo_senales, seguir_corriendo))
        p_threads = multiprocessing.Process(target=threads_worker, args=(snapshot, intervalo_threads, seguir_corriendo))
        p_scheduling = multiprocessing.Process(target=scheduling_worker, args=(snapshot, intervalo_scheduling, seguir_corriendo))
        p_sistema = multiprocessing.Process(target=sistema_worker, args=(snapshot, intervalo_sistema, seguir_corriendo))
        p_display = multiprocessing.Process(target=display_worker, args=(snapshot, verbose_flag, intervalos_por_nombre, seguir_corriendo))

        procesos = [p_recolector, p_resumen, p_fds, p_memoria, p_senales,
                    p_threads, p_scheduling, p_sistema, p_display]

        for p in procesos:
            p.start()

        pipe_senales = configurar_senales()

        apagando = False

        while not apagando:
            lectura, _, _ = select.select([pipe_senales], [], [], 1.0)

            if pipe_senales in lectura:
                numero_senal = os.read(pipe_senales, 1)[0]

                if numero_senal in (signal.SIGINT, signal.SIGTERM):
                    apagando = True

                elif numero_senal == signal.SIGHUP:
                    nueva_config = cargar_config_intervalos()
                    for nombre, valor_compartido in intervalos_por_nombre.items():
                        with valor_compartido.get_lock():
                            valor_compartido.value = nueva_config[nombre]

                    snapshot['config_filtro'] = cargar_filtro_default()
                    snapshot['config_revision'] = snapshot.get('config_revision', 0) + 1

                elif numero_senal == signal.SIGUSR1:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre_archivo = f"dump_{timestamp}.json"
                    try:
                        with open(nombre_archivo, "w") as f:
                            datos_dump = {k: dict(v) if hasattr(v, 'items') else v for k, v in snapshot.items()}
                            json.dump(datos_dump, f, indent=2, ensure_ascii=False, default=str)
                    except Exception:
                        pass

                elif numero_senal == signal.SIGUSR2:
                    with verbose_flag.get_lock():
                        verbose_flag.value = 0 if verbose_flag.value else 1

        with seguir_corriendo.get_lock():
            seguir_corriendo.value = 0

        for p in procesos:
            p.join(timeout=3)

        for p in procesos:
            if p.is_alive():
                p.terminate()
                p.join()

if __name__ == "__main__":
    main()