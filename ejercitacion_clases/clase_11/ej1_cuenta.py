"""Clase 11 - Ej 1: race condition en una cuenta y su corrección con Lock."""
import random
import threading
import time


class Cuenta:
    def __init__(self, saldo, segura):
        self.saldo = saldo
        self.lock = threading.Lock() if segura else None

    def _operar(self, delta):
        actual = self.saldo
        time.sleep(0.001)  # simula procesamiento: abre la ventana de la race
        if delta < 0 and actual < -delta:
            return False
        self.saldo = actual + delta
        return True

    def mover(self, delta):
        if self.lock is None:
            return self._operar(delta)
        with self.lock:  # toda la secuencia leer-modificar-escribir es una sola sección crítica
            return self._operar(delta)


def probar(segura):
    cuenta = Cuenta(1000, segura)
    netos = []  # depósitos menos retiros realmente aplicados, para saber qué saldo era correcto

    def trabajo():
        neto = 0
        for _ in range(100):
            delta = random.choice([10, -10])
            if cuenta.mover(delta):
                neto += delta
        netos.append(neto)  # list.append es atómico en CPython

    hilos = [threading.Thread(target=trabajo) for _ in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    esperado = 1000 + sum(netos)
    print(f"{'segura  ' if segura else 'insegura'} esperado={esperado} obtenido={cuenta.saldo}"
          f" -> {'OK' if esperado == cuenta.saldo else 'RACE CONDITION'}")


if __name__ == "__main__":
    probar(segura=False)
    probar(segura=True)
