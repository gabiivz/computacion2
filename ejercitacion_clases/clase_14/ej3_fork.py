"""Clase 14 - Ej 3 (obligatorio): los descuidos del fork. Zombies y SIGCHLD.

Uso:  python3 ej3_fork.py            -> corre cada modo 5 veces y resume
      python3 ej3_fork.py <modo>     -> una sola corrida (modos: sin_handler, sin_bucle, con_bucle, ign)
"""
import gc
import os
import signal
import socket
import subprocess
import sys
import time

N = 60


def hijos_zombie():
    """Cuenta mis hijos en estado Z leyendo /proc (como en el TP1)."""
    yo, zombies = os.getpid(), 0
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            campos = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
        except OSError:
            continue
        if int(campos[1]) == yo and campos[0] == "Z":  # campos[0]=estado, campos[1]=ppid
            zombies += 1
    return zombies


def una_corrida(modo):
    recogidos = [0]

    def sin_bucle(signum, frame):
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            recogidos[0] += pid > 0
        except ChildProcessError:
            pass

    def con_bucle(signum, frame):
        while True:  # las señales NO se encolan: un SIGCHLD puede representar varios hijos
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                return
            if pid == 0:
                return
            recogidos[0] += 1

    if modo == "sin_bucle":
        signal.signal(signal.SIGCHLD, sin_bucle)
    elif modo == "con_bucle":
        signal.signal(signal.SIGCHLD, con_bucle)
    elif modo == "ign":
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)  # el kernel cosecha solo, sin handler

    for _ in range(N):
        if os.fork() == 0:
            time.sleep(0.3)  # todos duermen lo mismo: mueren juntos
            os._exit(0)
    time.sleep(1.2)
    print(f"{modo} hijos={N} recogidos={recogidos[0]} zombies={hijos_zombie()}")


def demo_gc():
    def make():
        return socket.socket().fileno()  # el objeto muere al salir de la función

    fd = make()
    gc.collect()
    try:
        os.fstat(fd)
        print("gc: el fd sigue abierto")
    except OSError:
        print("gc: el fd ya está cerrado sin que nadie llame a close() (refcount -> __del__ -> close)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        una_corrida(sys.argv[1])
    else:
        demo_gc()
        for modo in ("sin_handler", "sin_bucle", "con_bucle", "ign"):
            for _ in range(5):
                print(subprocess.run([sys.executable, __file__, modo], capture_output=True,
                                     text=True).stdout.strip())
