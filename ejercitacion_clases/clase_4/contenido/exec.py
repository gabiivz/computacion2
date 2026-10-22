import os

pid = os.fork()

if pid == 0:
    # El hijo va a transformarse en 'ls'
    print(f"Hijo (PID {os.getpid()}): voy a convertirme en ls")
    os.execlp("ls", "ls", "-la", "/tmp")
    # Si llegamos aquí, exec falló
    print("Error: exec falló")
    os._exit(1)
else:
    print(f"Padre: esperando que el hijo {pid} termine...")
    os.wait()
    print("Padre: el hijo terminó")