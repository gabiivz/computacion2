import os

pid = os.fork()

if pid == 0:
    print(f"Soy el hijo: PID={os.getpid()}, padre={os.getppid()}")
    os._exit(0)
else:
    print(f"Soy el padre: PID={os.getpid()}, hijo={pid}")
    os.wait()
    print("Programa terminado")