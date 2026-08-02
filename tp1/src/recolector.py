import os
import time

def recolector_worker(snapshot, seguir_corriendo):
    """
    Busca los PIDs vivos en /proc y los guarda en el snapshot.
    Corre en un bucle infinito cada 1 segundo.
    """
    
    while seguir_corriendo.value:
        try:
            # os.listdir('/proc') trae TODAS las carpetas. 
            # Filtramos solo las que son números (PIDs)
            pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
            
            # Guardamos la lista oficial en el snapshot global
            snapshot['pids_activos'] = pids
            
            time.sleep(1) # Refresca la lista cada 1 segundo
            
        except KeyboardInterrupt:
            break