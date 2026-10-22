import os

pid = os.fork()

if pid < 0:
    print("Error: no se pudo crear el proceso")
elif pid == 0:
    # Rama del hijo
    print("Soy el hijo, voy a hacer trabajo específico de hijo")
    os._exit(0)  # Terminar el hijo
else:
    # Rama del padre
    print(f"Soy el padre, mi hijo es {pid}")
    # El padre típicamente espera al hijo o continúa con su trabajo