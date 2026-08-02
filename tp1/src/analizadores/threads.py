import os
import time

def analizar_threads(pid, historial_cpu_threads, tiempo_actual):
    """
    Lee /proc/<pid>/task/ para extraer información de cada hilo (LWP).
    """
    ruta_task = f"/proc/{pid}/task"
    lista_threads = []
    
    try:
        # Cada carpeta acá adentro es un TID (Thread ID)
        tids = os.listdir(ruta_task)
        
        for tid in tids:
            datos_thread = {
                "tid": tid,
                "nombre": "",
                "estado": "",
                "cpu_percent": 0.0,
                "vol_ctxt_switches": 0,
                "nonvol_ctxt_switches": 0
            }
            
            # 1. Nombre del hilo (comm)
            try:
                with open(f"{ruta_task}/{tid}/comm", "r") as f:
                    datos_thread["nombre"] = f.read().strip()
            except FileNotFoundError:
                continue 
                
            # 2. Context switches (voluntarios e involuntarios) desde status
            try:
                with open(f"{ruta_task}/{tid}/status", "r") as f:
                    for linea in f:
                        if linea.startswith("voluntary_ctxt_switches:"):
                            datos_thread["vol_ctxt_switches"] = int(linea.split(":")[1].strip())
                        elif linea.startswith("nonvoluntary_ctxt_switches:"):
                            datos_thread["nonvol_ctxt_switches"] = int(linea.split(":")[1].strip())
            except FileNotFoundError:
                pass
                
            # 3. Estado y CPU% (jiffies) desde stat
            try:
                with open(f"{ruta_task}/{tid}/stat", "r") as f:
                    linea = f.read()
                    fin_nombre = linea.rfind(')')
                    if fin_nombre != -1:
                        resto = linea[fin_nombre + 2:].split()
                        datos_thread["estado"] = resto[0]
                        
                        # utime y stime
                        utime = int(resto[11])
                        stime = int(resto[12])
                        total_jiffies = utime + stime
                        
                        # Calculamos el CPU% exacto de este hilo
                        clave_historial = f"{pid}_{tid}"
                        if clave_historial in historial_cpu_threads:
                            jiffies_ant, tiempo_ant = historial_cpu_threads[clave_historial]
                            delta_jiffies = total_jiffies - jiffies_ant
                            delta_tiempo = tiempo_actual - tiempo_ant
                            
                            if delta_tiempo > 0:
                                hz = 100.0
                                datos_thread["cpu_percent"] = 100.0 * (delta_jiffies / hz) / delta_tiempo
                                
                        historial_cpu_threads[clave_historial] = (total_jiffies, tiempo_actual)
            except FileNotFoundError:
                pass
                
            lista_threads.append(datos_thread)
            
        return lista_threads
        
    except (FileNotFoundError, PermissionError):
        return None

def threads_worker(snapshot, intervalo_compartido, seguir_corriendo):
    """
    Analizador de Threads (LWPs).
    Intervalo por defecto: 2 segundos.
    """
    historial_cpu_threads = {}
    
    while seguir_corriendo.value:
        try:
            pids_actuales = snapshot.get('pids_activos', [])
            tiempo_actual = time.time()
            diccionario_threads = {}
            
            for pid in pids_actuales:
                datos = analizar_threads(pid, historial_cpu_threads, tiempo_actual)
                if datos is not None:
                    diccionario_threads[pid] = datos
                    
            # Limpiamos la memoria del historial para los procesos que ya no existen
            pids_str = [str(p) for p in pids_actuales]
            historial_cpu_threads = {k: v for k, v in historial_cpu_threads.items() if k.split('_')[0] in pids_str}
            
            # Guardamos en el Snapshot Global
            snapshot['threads'] = diccionario_threads
            
            time.sleep(intervalo_compartido.value)
            
        except KeyboardInterrupt:
            break