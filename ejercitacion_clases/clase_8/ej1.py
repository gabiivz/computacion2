import multiprocessing
import os
import time

def hijo():
    print(f"[Hijo] Soy el proceso hijo con PID: {os.getpid()}")
    time.sleep(1)
    print("[Hijo] Terminando trabajo.")

if __name__ == '__main__':
    print(f"[Padre] Mi PID es: {os.getpid()}")
    
    # Creación del proceso
    p = multiprocessing.Process(target=hijo)
    
    p.start() # Equivalente al fork
    print(f"[Padre] Creé un hijo con PID: {p.pid}")
    
    p.join()  # Equivalente a os.wait()
    print("[Padre] El hijo terminó. Fin del programa.")