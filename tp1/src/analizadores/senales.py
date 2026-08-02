import time
import signal

def decodificar_mascara(mascara_hex):
    """
    Convierte una máscara hexadecimal de señales en una lista de nombres.

    """
    nombres_senales = []
    try:
        # Convertimos el string hexadecimal a un número entero
        mascara = int(mascara_hex, 16)
        
        # las señales estándar van de la 1 a la 64
        for i in range(1, 65):
            if (mascara >> (i - 1)) & 1:
                try:
                    nombre = signal.Signals(i).name
                    nombres_senales.append(nombre)
                except ValueError:
                    nombres_senales.append(f"SIGRT_{i}")
    except ValueError:
        pass
        
    return nombres_senales

def analizar_senales(pid):
    """Lee las máscaras de señales desde /proc/<pid>/status."""
    datos = {
        "SigBlk": [], # Señales bloqueadas
        "SigIgn": [], # Señales ignoradas
        "SigCgt": [], # Señales con handler propio (capturadas)
        "SigPnd": [], # Señales pendientes para el thread
        "ShdPnd": []  # Señales pendientes para el proceso global
    }
    
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for linea in f:
                # Buscamos solo las claves que nos importan
                partes = linea.split(":")
                if len(partes) < 2:
                    continue
                    
                clave = partes[0].strip()
                if clave in datos:
                    mascara_hex = partes[1].strip()
                    datos[clave] = decodificar_mascara(mascara_hex)
                    
    except (FileNotFoundError, PermissionError):
        return None
        
    return datos

def senales_worker(snapshot, intervalo_compartido, seguir_corriendo):
    """
    Analizador de Señales. 
    El TP pide que corra cada 10 segundos por defecto.
    """
    
    while seguir_corriendo.value:
        try:
            pids_actuales = snapshot.get('pids_activos', [])
            diccionario_senales = {}
            
            for pid in pids_actuales:
                datos = analizar_senales(pid)
                if datos is not None:
                    diccionario_senales[pid] = datos
                    
            snapshot['senales'] = diccionario_senales

            time.sleep(intervalo_compartido.value)
            
        except KeyboardInterrupt:
            break