import multiprocessing
import time

def tarea_vacia():
    pass

def medir_creacion(metodo, cantidad=100):
    # Obtenemos el contexto específico ('fork' o 'spawn')
    ctx = multiprocessing.get_context(metodo)
    procesos = []
    
    inicio = time.time()
    
    # Creamos e iniciamos
    for _ in range(cantidad):
        p = ctx.Process(target=tarea_vacia)
        procesos.append(p)
        p.start()
        
    # Esperamos que terminen
    for p in procesos:
        p.join()
        
    fin = time.time()
    tiempo_total = fin - inicio
    print(f"Método '{metodo}': Creación de {cantidad} procesos tomó {tiempo_total:.4f} segundos.")

if __name__ == '__main__':
    print("Iniciando medición...")
    # El método 'fork' (por defecto en Linux) clona la memoria del proceso, es muy rápido.
    medir_creacion('fork')
    
    # El método 'spawn' lanza un nuevo intérprete de Python desde cero, es más lento pero más seguro (por defecto en Windows/macOS).
    medir_creacion('spawn')