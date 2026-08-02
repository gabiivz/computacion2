import time
import os

def leer_cpu_global(historial, tiempo_actual):
    """Calcula el porcentaje de uso global de la CPU """
    try:
        with open('/proc/stat', 'r') as f:
            # La primera línea de stat tiene el total de la CPU
            linea = f.readline()
            valores = [int(x) for x in linea.split()[1:]]
            
            idle = valores[3] + valores[4]
            total = sum(valores)
            
            porcentajes = {"user": 0.0, "system": 0.0, "idle": 0.0, "iowait": 0.0, "total": 0.0}
            
            if "ultimo_total" in historial:
                delta_total = total - historial["ultimo_total"]
                delta_idle = idle - historial["ultimo_idle"]
                
                if delta_total > 0:
                    porcentajes["total"] = 100.0 * (delta_total - delta_idle) / delta_total
                    porcentajes["user"] = 100.0 * (valores[0] - historial["ultimo_user"]) / delta_total
                    porcentajes["system"] = 100.0 * (valores[2] - historial["ultimo_system"]) / delta_total
                    porcentajes["idle"] = 100.0 * (valores[3] - historial["ultimo_idle_puro"]) / delta_total
                    porcentajes["iowait"] = 100.0 * (valores[4] - historial["ultimo_iowait"]) / delta_total
                    
            historial["ultimo_total"] = total
            historial["ultimo_idle"] = idle
            historial["ultimo_user"] = valores[0]
            historial["ultimo_system"] = valores[2]
            historial["ultimo_idle_puro"] = valores[3]
            historial["ultimo_iowait"] = valores[4]
            
            return porcentajes
    except FileNotFoundError:
        return None

def sistema_worker(snapshot, intervalo_compartido, seguir_corriendo):
    """
    Analizador de estadísticas globales del Sistema.
    Intervalo por defecto: 2 segundos.
    """
    historial_cpu = {}
    
    while seguir_corriendo.value:
        try:
            datos = {
                "cpu_global": leer_cpu_global(historial_cpu, time.time()),
                "load_avg": [],
                "memoria": {},
                "uptime": 0,
                "btime": 0,
                "procesos_stats": {"total": 0, "running": 0, "sleeping": 0, "zombies": 0, "threads": 0},
                "top_cpu": [],
                "top_ram": []
            }
            
            # 1. Load Average
            try:
                with open('/proc/loadavg', 'r') as f:
                    datos["load_avg"] = " ".join(f.read().split()[:3])
            except FileNotFoundError: pass
            
            # 2. Meminfo 
            try:
                with open('/proc/meminfo', 'r') as f:
                    mem_temp = {}
                    for linea in f:
                        if linea.startswith(("MemTotal:", "MemFree:", "Buffers:", "Cached:", "SwapTotal:", "SwapFree:")):
                            partes = linea.split()
                            mem_temp[partes[0].replace(":", "")] = partes[1] + " KB"
                    datos["memoria"] = {
                        "total": mem_temp.get("MemTotal", "?"),
                        "free": mem_temp.get("MemFree", "?"),
                        "buffers": mem_temp.get("Buffers", "?"),
                        "cached": mem_temp.get("Cached", "?"),
                        "swap": f"Tot: {mem_temp.get('SwapTotal', '?')} / Lib: {mem_temp.get('SwapFree', '?')}"
                    }
            except FileNotFoundError: pass
            
            # 3. Uptime y Boot time en formato texto legible
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_sec = float(f.read().split()[0])
                    datos["uptime"] = f"{uptime_sec / 3600:.1f} horas"
                with open('/proc/stat', 'r') as f:
                    for linea in f:
                        if linea.startswith("btime"):
                            datos["btime"] = int(linea.split()[1])
            except FileNotFoundError: pass
            
            # 4. Estadísticas sumadas desde nuestro propio Snapshot (Resumen y Threads)
            resumen = snapshot.get('resumen', {})
            threads = snapshot.get('threads', {})
            
            total_proc = len(resumen)
            total_threads = sum(len(hilos) for hilos in threads.values()) if threads else 0
            run, sleep, zomb = 0, 0, 0
            
            for proc in resumen.values():
                estado = proc.get("estado", "?")
                if estado == "R": run += 1
                elif estado in ("S", "D"): sleep += 1
                elif estado == "Z": zomb += 1
                
            datos["procesos_stats"] = {
                "total": total_proc,
                "running": run,
                "sleeping": sleep,
                "zombies": zomb,
                "threads": total_threads
            }
            
            # 5. Derivar Top 3 por CPU y por Memoria directamente del snapshot actual
            lista_procesos = list(resumen.items())
            
            # Ordenar por CPU descendente
            top_cpu_sorted = sorted(lista_procesos, key=lambda x: x[1].get("cpu_percent", 0.0), reverse=True)[:3]
            datos["top_cpu"] = [f"PID {p[0]} ({p[1].get('comando', '?')[:15]}): {p[1].get('cpu_percent', 0.0):.1f}%" for p in top_cpu_sorted]
            
            # Ordenar por Memoria (VmRSS) descendente si está disponible
            memoria_procs = snapshot.get('memoria', {})
            top_ram_sorted = sorted(lista_procesos, key=lambda x: float(str(memoria_procs.get(x[0], {}).get('vmrss', '0')).replace('kB','').strip() or 0), reverse=True)[:3]
            datos["top_ram"] = [f"PID {p[0]} ({p[1].get('comando', '?')[:15]})" for p in top_ram_sorted]

            # 6. Guardar en la clave CORRECTA que busca la interfaz
            snapshot['globales'] = datos
            time.sleep(intervalo_compartido.value)
            
        except KeyboardInterrupt:
            break