"""Clase 11 - Ej 5 (obligatorio): Readers-Writers Lock con Condition.

Variante con preferencia de escritores: si hay un escritor esperando, los lectores
nuevos esperan. Evita que una avalancha de lectores deje al escritor en starvation.
"""
import random
import threading
import time


class ReadWriteLock:
    def __init__(self):
        self.readers = 0
        self.writing = False
        self.writers_waiting = 0
        self.cond = threading.Condition()  # un solo lock + una sola condición alcanza

    def acquire_read(self):
        with self.cond:
            while self.writing or self.writers_waiting > 0:
                self.cond.wait()
            self.readers += 1

    def release_read(self):
        with self.cond:
            self.readers -= 1
            if self.readers == 0:
                self.cond.notify_all()

    def acquire_write(self):
        with self.cond:
            self.writers_waiting += 1
            while self.writing or self.readers > 0:
                self.cond.wait()
            self.writers_waiting -= 1
            self.writing = True

    def release_write(self):
        with self.cond:
            self.writing = False
            self.cond.notify_all()


class _Ctx:
    def __init__(self, enter, exit_):
        self._enter, self._exit = enter, exit_

    def __enter__(self):
        self._enter()

    def __exit__(self, *exc):
        self._exit()


def ReadLock(rw):
    return _Ctx(rw.acquire_read, rw.release_read)


def WriteLock(rw):
    return _Ctx(rw.acquire_write, rw.release_write)


rw = ReadWriteLock()
datos = {"valor": 0, "lecturas": 0, "escrituras": 0}
estado = {"lectores_activos": 0, "max_lectores": 0, "violaciones": 0}
meta = threading.Lock()  # protege los contadores de verificación


def lector(i):
    for _ in range(5):
        with ReadLock(rw):
            with meta:
                estado["lectores_activos"] += 1
                estado["max_lectores"] = max(estado["max_lectores"], estado["lectores_activos"])
            _ = datos["valor"]
            time.sleep(random.uniform(0.02, 0.06))
            with meta:
                estado["lectores_activos"] -= 1
                datos["lecturas"] += 1
        time.sleep(random.uniform(0.02, 0.05))


def escritor(i):
    for k in range(3):
        with WriteLock(rw):
            with meta:
                if estado["lectores_activos"] > 0:  # hay lectores mientras escribo: violación
                    estado["violaciones"] += 1
            datos["valor"] = i * 100 + k
            datos["escrituras"] += 1
            time.sleep(0.05)
        time.sleep(random.uniform(0.05, 0.1))


if __name__ == "__main__":
    hilos = [threading.Thread(target=lector, args=(i,)) for i in range(5)]
    hilos += [threading.Thread(target=escritor, args=(i,)) for i in range(2)]
    random.shuffle(hilos)
    t0 = time.time()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    print(f"lecturas={datos['lecturas']} (25) escrituras={datos['escrituras']} (6) "
          f"max lectores simultáneos={estado['max_lectores']} violaciones={estado['violaciones']} "
          f"[{time.time() - t0:.2f}s]")
