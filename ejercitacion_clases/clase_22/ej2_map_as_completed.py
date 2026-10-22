"""Clase 22 - Ej 2 (obligatorio): Executor.map vs as_completed vs wait."""
import time
from concurrent.futures import (FIRST_COMPLETED, FIRST_EXCEPTION, ThreadPoolExecutor, as_completed, wait)

T0 = time.perf_counter()


def ahora():
    return time.perf_counter() - T0


def trabajo(nombre, segundos, falla=False):
    time.sleep(segundos)
    if falla:
        raise RuntimeError(f"{nombre} falló")
    return f"{nombre} ({segundos}s)"


ENTRADAS = [("lenta", 0.6), ("media", 0.3), ("rapida", 0.1)]


def con_map():
    print("--- map (entrega en orden de ENTRADA) ---")
    with ThreadPoolExecutor(3) as ex:
        t0 = time.perf_counter()
        for r in ex.map(trabajo, *zip(*ENTRADAS)):
            print(f"  {time.perf_counter() - t0:.2f}s recibí {r}")
        print(f"  total {time.perf_counter() - t0:.2f}s")


def con_as_completed():
    print("--- as_completed (entrega en orden de TERMINACIÓN) ---")
    with ThreadPoolExecutor(3) as ex:
        t0 = time.perf_counter()
        futuros = [ex.submit(trabajo, n, s) for n, s in ENTRADAS]
        for f in as_completed(futuros):
            print(f"  {time.perf_counter() - t0:.2f}s recibí {f.result()}")
        print(f"  total {time.perf_counter() - t0:.2f}s")


def correspondencia():
    print("--- patrón del diccionario Future -> entrada (qué falló) ---")
    urls = {"a": (0.1, False), "b": (0.2, True), "c": (0.15, False), "d": (0.05, True), "e": (0.1, False)}
    with ThreadPoolExecutor(5) as ex:
        origen = {ex.submit(trabajo, k, s, f): k for k, (s, f) in urls.items()}  # Future es hashable (identidad)
        for f in as_completed(origen):
            try:
                print(f"  {origen[f]}: OK {f.result()}")
            except Exception as e:
                print(f"  {origen[f]}: FALLÓ -> {e}")


def con_wait():
    print("--- wait ---")
    with ThreadPoolExecutor(4) as ex:
        fs = [ex.submit(trabajo, "x", 0.5), ex.submit(trabajo, "y", 0.1, True), ex.submit(trabajo, "z", 0.8)]
        hechos, pendientes = wait(fs, return_when=FIRST_EXCEPTION)
        print(f"  FIRST_EXCEPTION: vuelve apenas falla uno -> hechos={len(hechos)} pendientes={len(pendientes)}")
        for f in pendientes:
            f.cancel()  # los que ya corren no se pueden cancelar; los que no empezaron sí

    print("--- primera respuesta de tres servidores ---")
    with ThreadPoolExecutor(3) as ex:
        t0 = time.perf_counter()
        fs = [ex.submit(trabajo, f"srv{i}", d) for i, d in enumerate((0.5, 0.1, 0.3))]
        hechos, pendientes = wait(fs, return_when=FIRST_COMPLETED)
        print(f"  {time.perf_counter() - t0:.2f}s primera: {next(iter(hechos)).result()}; "
              f"cancelar() de los otros devuelve {[f.cancel() for f in pendientes]} (ya estaban corriendo)")


if __name__ == "__main__":
    con_map()
    con_as_completed()
    correspondencia()
    con_wait()
