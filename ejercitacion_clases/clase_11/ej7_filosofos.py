"""Clase 11 - Ej 7: filósofos comensales. Deadlock (A), jerarquía (B), semáforo (C), medición (D)."""
import random
import sys
import threading
import time

NUM = 5
COMIDAS = 3


def correr(estrategia, timeout=5):
    tenedores = [threading.Lock() for _ in range(NUM)]
    barrera = threading.Barrier(NUM)  # fuerza el entrelazado malo (parte A)
    sem = threading.Semaphore(NUM - 1)
    tiempos = [0.0] * NUM

    def comer():
        time.sleep(random.uniform(0.01, 0.03))

    def filosofo(i):
        izq, der = i, (i + 1) % NUM
        t0 = time.time()
        for _ in range(COMIDAS):
            if estrategia == "ingenuo":
                with tenedores[izq]:
                    barrera.wait()
                    with tenedores[der]:
                        comer()
            elif estrategia == "jerarquia":
                # ordenar los ÍNDICES: siempre el menor primero -> no hay espera circular
                primero, segundo = sorted((izq, der))
                with tenedores[primero], tenedores[segundo]:
                    comer()
            elif estrategia == "semaforo":
                with sem:  # a lo sumo 4 compiten: siempre queda un tenedor libre para alguien
                    with tenedores[izq], tenedores[der]:
                        comer()
        tiempos[i] = time.time() - t0

    hilos = [threading.Thread(target=filosofo, args=(i,), daemon=True) for i in range(NUM)]
    t0 = time.time()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout)
    colgado = any(h.is_alive() for h in hilos)
    return colgado, time.time() - t0, tiempos


if __name__ == "__main__":
    for est in ("ingenuo", "jerarquia", "semaforo"):
        colgado, total, tiempos = correr(est, timeout=2 if est == "ingenuo" else 10)
        if colgado:
            print(f"{est:10s} DEADLOCK (sigue colgado tras el timeout)")
        else:
            print(f"{est:10s} ok total={total:.2f}s por filósofo={[round(t, 2) for t in tiempos]}")
    sys.exit(0)  # los hilos del caso ingenuo son daemon: no impiden salir
