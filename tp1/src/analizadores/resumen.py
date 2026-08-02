import time
import pwd

def analizar_proceso(pid, historial_cpu, tiempo_actual):
    """
    Extrae toda la información obligatoria de la vista Resumen para un PID.
    """
    datos = {
        "pid": pid,
        "ppid": "?",
        "uid": "?",
        "gid": "?",
        "usuario": "?",
        "estado": "?",
        "comando": "?",
        "cpu_percent": 0.0,
        "threads": 0
    }
    
    # 1. Comando completo (/proc/<pid>/cmdline)
    try:
        with open(f"/proc/{pid}/cmdline", "r") as f:
            cmd = f.read().replace('\x00', ' ').strip()
            datos["comando"] = cmd
    except FileNotFoundError:
        return None 
        
    # 2. PPID, UID, GID y Threads (/proc/<pid>/status)
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for linea in f:
                if linea.startswith("PPid:"):
                    datos["ppid"] = linea.split()[1]
                elif linea.startswith("Uid:"):
                    uid = int(linea.split()[1])
                    datos["uid"] = uid
                    # Convertimos el número de UID a nombre de usuario
                    try:
                        datos["usuario"] = pwd.getpwuid(uid).pw_name
                    except KeyError:
                        datos["usuario"] = str(uid)
                elif linea.startswith("Gid:"):
                    datos["gid"] = linea.split()[1]
                elif linea.startswith("Threads:"):
                    datos["threads"] = int(linea.split()[1])
    except FileNotFoundError:
        return None

    # 3. Estado y Jiffies para CPU% (/proc/<pid>/stat)
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            linea = f.read()
            fin_nombre = linea.rfind(')')
            if fin_nombre != -1:
                resto = linea[fin_nombre + 2:].split()
                datos["estado"] = resto[0]
                utime = int(resto[11])
                stime = int(resto[12])
                total_jiffies = utime + stime
                
                if pid in historial_cpu:
                    jiffies_anteriores, tiempo_anterior = historial_cpu[pid]
                    delta_jiffies = total_jiffies - jiffies_anteriores
                    delta_tiempo = tiempo_actual - tiempo_anterior
                    
                    if delta_tiempo > 0:
                        hz = 100.0
                        datos["cpu_percent"] = 100.0 * (delta_jiffies / hz) / delta_tiempo
                        
                # Guardamos los jiffies actuales para el próximo ciclo
                historial_cpu[pid] = (total_jiffies, tiempo_actual)
    except FileNotFoundError:
        return None

    if not datos["comando"]:
        datos["comando"] = f"[{pid}] (kernel thread)"

    return datos

def resumen_worker(snapshot, intervalo_compartido, seguir_corriendo):
    """Analizador de la vista Resumen."""
    
    # Este diccionario local guarda la lectura anterior de CPU de cada PID
    historial_cpu = {}
    
    while seguir_corriendo.value:
        try:
            pids_actuales = snapshot.get('pids_activos', [])
            tiempo_actual = time.time()
            diccionario_resumen = {}
            
            for pid in pids_actuales:
                datos = analizar_proceso(pid, historial_cpu, tiempo_actual)
                if datos:
                    diccionario_resumen[pid] = datos
            
            # Limpiamos el historial para no perder memoria RAM con procesos muertos
            historial_cpu = {pid: v for pid, v in historial_cpu.items() if pid in pids_actuales}
            
            # Subimos el bloque de datos al Snapshot Global
            snapshot['resumen'] = diccionario_resumen
            
            time.sleep(intervalo_compartido.value)
            
        except KeyboardInterrupt:
            break