"""Clase 18 - Ej 2 (obligatorio): un event loop cooperativo escrito desde cero con generadores."""
import heapq
import time
from collections import deque

llamadas_next = 0


# ---------- Parte A: intercalado ----------
def tarea(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f"  [{nombre}] paso {i}/{pasos}")
        yield  # cede el control al scheduler


def scheduler(tareas):
    global llamadas_next
    pendientes = deque(tareas)
    while pendientes:
        t = pendientes.popleft()
        try:
            llamadas_next += 1
            next(t)  # reanuda hasta el próximo yield
            pendientes.append(t)  # cedió: vuelve al final de la cola
        except StopIteration:
            pass  # terminó: no vuelve


# ---------- Parte B: la cooperación es obligatoria ----------
def tarea_egoista(nombre):
    print(f"  [{nombre}] me pongo a calcular")
    time.sleep(1)  # NO cede el control: congela a todos
    print(f"  [{nombre}] listo")
    yield


# ---------- Parte C/D: tiempo ----------
def dormir(segundos):
    """Cede informando hasta cuándo no quiere ser reanudada."""
    yield time.monotonic() + segundos


def scheduler_tiempo(tareas):
    listos = deque(tareas)
    durmiendo = []  # heap de (despertar, id, tarea)
    n = 0
    while listos or durmiendo:
        ahora = time.monotonic()
        while durmiendo and durmiendo[0][0] <= ahora:
            listos.append(heapq.heappop(durmiendo)[2])
        if not listos:  # todos duermen: esperamos al más cercano SIN bloquear a nadie más
            time.sleep(max(0, durmiendo[0][0] - time.monotonic()))
            continue
        t = listos.popleft()
        try:
            pedido = next(t)
        except StopIteration:
            continue
        if pedido is None:
            listos.append(t)
        else:
            n += 1
            heapq.heappush(durmiendo, (pedido, n, t))


def tarea_lenta(nombre, espera):
    print(f"  [{nombre}] empiezo, espero {espera}s")
    yield from dormir(espera)  # yield from delega: el yield de dormir sale hasta el scheduler
    print(f"  [{nombre}] desperté")


def tarea_mal(nombre, espera):
    print(f"  [{nombre}] empiezo")
    dormir(espera)  # SIN yield from: solo crea el generador y lo tira; no espera nada y no falla
    print(f"  [{nombre}] terminé SIN haber esperado")
    yield


if __name__ == "__main__":
    print("A: tres tareas de 2, 3 y 1 pasos")
    scheduler([tarea("A", 2), tarea("B", 3), tarea("C", 1)])
    print(f"   next() llamado {llamadas_next} veces (6 pasos + 3 StopIteration)")

    print("B: una tarea egoísta en el medio")
    t0 = time.time()
    scheduler([tarea("A", 2), tarea_egoista("EGOISTA"), tarea("B", 2)])
    print(f"   total {time.time() - t0:.1f}s: A y B no avanzaron durante el segundo del egoísta")

    print("C: tres tareas que esperan 0.15 s cada una")
    t0 = time.time()
    scheduler_tiempo([tarea_lenta(f"T{i}", 0.15) for i in range(3)])
    print(f"   total {time.time() - t0:.2f}s (suma sería 0.45s): esperan a la vez")

    print("D: dormir() sin yield from")
    t0 = time.time()
    scheduler_tiempo([tarea_mal("M", 0.5)])
    print(f"   total {time.time() - t0:.2f}s: no esperó nada y no hubo error")
