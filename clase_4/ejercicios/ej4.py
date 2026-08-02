import os
import time

pid = os.fork()

if pid == 0:
    print(f"[Hijo PID={os.getpid()}] termino inmediatamente")
    os._exit(0)
else:
    print(f"[Padre PID={os.getpid()}] creé hijo {pid}, no lo voy a esperar")
    print("Mirá con: ps aux | grep -E 'Z|defunct'")
    time.sleep(30)
    
    os.wait()
    print("Hijo recogido, ya no es zombie")