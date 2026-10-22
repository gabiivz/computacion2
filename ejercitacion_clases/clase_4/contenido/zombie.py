import os
import time

# Crear un zombie
pid = os.fork()
if pid == 0:
    # El hijo termina inmediatamente
    print("Hijo: terminando")
    os._exit(0)
else:
    # El padre NO hace wait - el hijo queda zombie
    print(f"Padre: creé hijo {pid}, pero no voy a esperarlo")
    print("Ejecutá 'ps aux | grep Z' en otra terminal para ver el zombie")
    time.sleep(30)  # Mantener el padre vivo