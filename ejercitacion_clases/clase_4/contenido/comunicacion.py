import os

# Configurar antes del fork
os.environ["MODO"] = "produccion"
os.environ["DEBUG"] = "0"

pid = os.fork()

if pid == 0:
    # El hijo ve las variables
    print(f"Hijo: MODO={os.environ.get('MODO')}")
    os._exit(0)
else:
    os.wait()