import time

def parsear_politica(codigo):
    """
    Convierte el número de política de scheduling de Linux a un nombre legible.
    """
    politicas = {
        "0": "OTHER",   
        "1": "FIFO",    
        "2": "RR",      
        "3": "BATCH",    
        "5": "IDLE",     
        "6": "DEADLINE"  
    }
    return politicas.get(str(codigo), f"UNKNOWN({codigo})")

def analizar_scheduling(pid):
    """Extrae las estadísticas de planificación del proceso."""
    datos = {
        "nice": 0,
        "priority": 0,
        "policy": "UNKNOWN",
        "rt_priority": 0,
        "cpu_affinity": "",
        "vol_ctxt_switches": 0,
        "nonvol_ctxt_switches": 0,
        "utime": 0,
        "stime": 0,
        "sid": 0,
        "pgid": 0
    }

    # 1. Datos numéricos principales (/proc/<pid>/stat)
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            linea = f.read()
            fin_nombre = linea.rfind(')')
            if fin_nombre != -1:
                resto = linea[fin_nombre + 2:].split()
                
                datos["pgid"] = int(resto[2])    # Campo 5
                datos["sid"] = int(resto[3])     # Campo 6
                datos["utime"] = int(resto[11])  # Campo 14
                datos["stime"] = int(resto[12])  # Campo 15
                datos["priority"] = int(resto[15]) # Campo 18
                datos["nice"] = int(resto[16])   # Campo 19
                
                if len(resto) > 38:
                    datos["rt_priority"] = int(resto[37]) # Campo 40
                    datos["policy"] = parsear_politica(resto[38]) # Campo 41
    except (FileNotFoundError, IndexError):
        return None
        
    # 2. Afinidad y Context Switches (/proc/<pid>/status)
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for linea in f:
                if linea.startswith("Cpus_allowed_list:"):
                    datos["cpu_affinity"] = linea.split(":")[1].strip()
                elif linea.startswith("voluntary_ctxt_switches:"):
                    datos["vol_ctxt_switches"] = int(linea.split(":")[1].strip())
                elif linea.startswith("nonvoluntary_ctxt_switches:"):
                    datos["nonvol_ctxt_switches"] = int(linea.split(":")[1].strip())
    except FileNotFoundError:
        pass
        
    return datos

def scheduling_worker(snapshot, intervalo_compartido, seguir_corriendo):
    """
    Worker del analizador de Scheduling.
    Intervalo por defecto: 10 segundos.
    """
    
    while seguir_corriendo.value:
        try:
            pids_actuales = snapshot.get('pids_activos', [])
            diccionario_sched = {}
            
            for pid in pids_actuales:
                datos = analizar_scheduling(pid)
                if datos is not None:
                    diccionario_sched[pid] = datos
                    
            snapshot['scheduling'] = diccionario_sched
            
            time.sleep(intervalo_compartido.value)
            
        except KeyboardInterrupt:
            break