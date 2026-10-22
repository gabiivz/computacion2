import os

pid = os.fork()

if pid == 0:
    print("Hijo: trabajando...")
    os._exit(42)  # Terminar con código 42
else:
    print(f"Padre: esperando al hijo {pid}")

    # wait() bloquea hasta que ALGÚN hijo termine
    hijo_terminado, status = os.wait()

    # Extraer el código de salida
    if os.WIFEXITED(status):
        codigo = os.WEXITSTATUS(status)
        print(f"Hijo {hijo_terminado} terminó normalmente con código {codigo}")
    elif os.WIFSIGNALED(status):
        señal = os.WTERMSIG(status)
        print(f"Hijo {hijo_terminado} terminado por señal {señal}")