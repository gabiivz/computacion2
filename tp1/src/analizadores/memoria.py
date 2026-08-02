import time

def analizar_memoria(pid):
    """
    Extrae la información de memoria de /proc/<pid>/status, stat y maps.
    """
    datos = {
        "vmsize": "0 kB",
        "vmrss": "0 kB",
        "vmdata": "0 kB",
        "vmstk": "0 kB",
        "vmexe": "0 kB",
        "vmlib": "0 kB",
        "vmhwm": "0 kB",
        "vmswap": "0 kB",
        "minflt": 0,
        "majflt": 0,
        "segmentos": {"heap": 0, "stack": 0, "text": 0, "data": 0, "shared": 0, "otros": 0}
    }

    # 1. Tamaños principales de memoria (/proc/<pid>/status)
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for linea in f:
                if linea.startswith("VmSize:"):
                    datos["vmsize"] = linea.split(":")[1].strip()
                elif linea.startswith("VmRSS:"):
                    datos["vmrss"] = linea.split(":")[1].strip()
                elif linea.startswith("VmData:"):
                    datos["vmdata"] = linea.split(":")[1].strip()
                elif linea.startswith("VmStk:"):
                    datos["vmstk"] = linea.split(":")[1].strip()
                elif linea.startswith("VmExe:"):
                    datos["vmexe"] = linea.split(":")[1].strip()
                elif linea.startswith("VmLib:"):
                    datos["vmlib"] = linea.split(":")[1].strip()
                elif linea.startswith("VmHWM:"):
                    datos["vmhwm"] = linea.split(":")[1].strip()
                elif linea.startswith("VmSwap:"):
                    datos["vmswap"] = linea.split(":")[1].strip()
    except FileNotFoundError:
        return None 

    # 2. Page Faults (/proc/<pid>/stat -> campos 10 al 13)
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            linea = f.read()
            fin_nombre = linea.rfind(')')
            if fin_nombre != -1:
                resto = linea[fin_nombre + 2:].split()
                datos["minflt"] = int(resto[7]) + int(resto[8])   # Proceso + sus hijos
                datos["majflt"] = int(resto[9]) + int(resto[10])  # Proceso + sus hijos
    except (FileNotFoundError, IndexError, ValueError):
        pass

    # 3. Segmentos de memoria mapeados (/proc/<pid>/maps)
    try:
        with open(f"/proc/{pid}/maps", "r") as f:
            for linea in f:
                partes = linea.split()
                if len(partes) < 2:
                    continue
                
                perms = partes[1]
                etiqueta = partes[-1] if len(partes) >= 6 else ""

                if "[heap]" in etiqueta:
                    datos["segmentos"]["heap"] += 1
                elif "[stack]" in etiqueta:
                    datos["segmentos"]["stack"] += 1
                elif "s" in perms:  # Permiso 's' indica memoria compartida (shared)
                    datos["segmentos"]["shared"] += 1
                elif "x" in perms:  # Ejecutable -> Código / Text
                    datos["segmentos"]["text"] += 1
                elif "w" in perms:  # Escritura privada -> Variables / Data
                    datos["segmentos"]["data"] += 1
                else:
                    datos["segmentos"]["otros"] += 1
    except (FileNotFoundError, PermissionError):
        pass # Ignoramos si murió o si es un proceso de root protegido
    swap_value = "0 kB"
    ruta_status = f"/proc/{pid}/status"

    try:
        with open(ruta_status, "r") as f:
            for linea in f:
                if linea.startswith("VmSwap:"):
                    swap_value = linea.split(":")[1].strip()
                    break
    except Exception:
        swap_value = "N/A"
    datos["swap"] = swap_value

    return datos

def memoria_worker(snapshot, intervalo_compartido, seguir_corriendo):
    """
    Analizador que procesa la vista de Memoria.
    Intervalo por defecto: 3 segundos.
    """
    
    while seguir_corriendo.value:
        try:
            pids_actuales = snapshot.get('pids_activos', [])
            diccionario_memoria = {}
            
            for pid in pids_actuales:
                datos = analizar_memoria(pid)
                if datos is not None:
                    diccionario_memoria[pid] = datos
            
            # Subimos los resultados al Snapshot Global
            snapshot['memoria'] = diccionario_memoria
            
            time.sleep(intervalo_compartido.value)
            
        except KeyboardInterrupt:
            break