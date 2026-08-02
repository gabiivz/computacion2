import multiprocessing
import time

def productor(queue):
    for i in range(1, 11):
        item = f"Item-{i}"
        print(f"[Productor] Generando {item}...")
        queue.put(item)
        time.sleep(0.1) # Simulando tiempo de creación
        
    # Enviamos un "centinela" para avisar que terminamos
    queue.put(None)
    print("[Productor] Producción finalizada.")

def consumidor(queue):
    while True:
        item = queue.get()
        if item is None: # Chequeamos el centinela
            print("[Consumidor] No hay más items. Finalizando.")
            break
        print(f"[Consumidor] Procesando {item}...")
        time.sleep(0.2) # Simulando tiempo de procesamiento

if __name__ == '__main__':
    q = multiprocessing.Queue()

    p1 = multiprocessing.Process(target=productor, args=(q,))
    p2 = multiprocessing.Process(target=consumidor, args=(q,))

    p1.start()
    p2.start()

    p1.join()
    p2.join()