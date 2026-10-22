import multiprocessing
import time
import random

def worker(id_worker):
    tiempo_espera = random.uniform(0.5, 2.0)
    print(f"Worker {id_worker} iniciando... (dormirá {tiempo_espera:.2f}s)")
    time.sleep(tiempo_espera)
    print(f"Worker {id_worker} finalizado.")

if __name__ == '__main__':
    procesos = []
    inicio_total = time.time()

    # Lanzamos los 5 workers
    for i in range(5):
        p = multiprocessing.Process(target=worker, args=(i,))
        procesos.append(p)
        p.start()

    # Esperamos a que todos terminen
    for p in procesos:
        p.join()

    fin_total = time.time()
    print(f"\nTiempo total de ejecución: {fin_total - inicio_total:.2f} segundos.")
    # El tiempo total será cercano al worker que más haya tardado, no a la suma de todos.