import os
import time

def pool_workers():
    # Nuestra lista de trabajos pendientes
    tareas = ["Tarea A", "Tarea B", "Tarea C", "Tarea D", "Tarea E", "Tarea F"]
    
    max_workers = 3  # El límite 'N' de hijos que permitimos correr a la vez
    hijos_activos = set() # Guardamos los PIDs de los hijos que están trabajando

    print(f"[Padre] Iniciando pool. {len(tareas)} tareas, {max_workers} workers permitidos.")

    # El bucle principal vive MIENTRAS haya tareas por hacer O hijos todavía trabajando
    while tareas or hijos_activos:
        
        # 1. LLENAR EL POOL: Mientras haya lugar (ventanillas libres) y queden tareas
        while len(hijos_activos) < max_workers and tareas:
            tarea_actual = tareas.pop(0) # Sacamos la primera tarea de la lista
            
            pid = os.fork()
            
            if pid == 0:
                # HIJO (Worker)

                print(f"  -> [Worker PID {os.getpid()}] Arrancando: {tarea_actual}")
                time.sleep(2) # Simulamos que resolver la tarea toma 2 segundos
                print(f"  <- [Worker PID {os.getpid()}] Terminada: {tarea_actual}")
                
                # CRÍTICO: El hijo DEBE morir acá, sino intentará seguir ejecutando el bucle
                os._exit(0) 
            else:
                # PADRE
                # Registramos al nuevo trabajador en nuestro conjunto de activos
                hijos_activos.add(pid)
        
        # 2. ESPERAR RESULTADOS: Si el pool está lleno (o ya no hay tareas pero sí hijos activos)
        if hijos_activos:
            # os.wait() bloquea al padre. Cuando CUALQUIER hijo haga os._exit(0), avanza.
            pid_terminado, status = os.wait()
            
            # Borramos al hijo que terminó de nuestra lista de activos (liberamos la ventanilla)
            hijos_activos.remove(pid_terminado)
            print(f"[Padre] El Worker {pid_terminado} se fue a su casa. Espacio liberado.")
            
    print("[Padre] ¡Fila vacía! Todas las tareas fueron procesadas.")

if __name__ == "__main__":
    pool_workers()