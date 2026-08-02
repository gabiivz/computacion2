import os
import time
import random

hijos = []
for i in range(5):
    pid = os.fork()
    if pid == 0:
        duracion = random.uniform(0.5, 2)
        print(f"[Hijo {i}] PID={os.getpid()}, dormiré {duracion:.1f}s")
        time.sleep(duracion)
        os._exit(i)
    else:
        hijos.append((pid, i))

for pid, i in hijos:
    _, status = os.waitpid(pid, 0)
    codigo = os.WEXITSTATUS(status)
    print(f"Hijo {i} (PID {pid}) terminó con código {codigo}")