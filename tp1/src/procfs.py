import os

def obtener_datos_basicos(pid):
    """
    Lee /proc/<pid>/status y extrae Nombre, Estado y Threads.
    Retorna un diccionario con la información.
    """
    ruta_status = f"/proc/{pid}/status"
    
    datos = {
        "pid": pid,
        "nombre": "Desconocido",
        "estado": "Desconocido",
        "threads": 0
    }
    
    try:
        # Abrimos el archivo en modo lectura
        with open(ruta_status, "r") as f:
            for linea in f:
                # Buscamos las claves exactas que nos pide el TP
                if linea.startswith("Name:"):
                    datos["nombre"] = linea.split(":")[1].strip()
                
                elif linea.startswith("State:"):
                    datos["estado"] = linea.split(":")[1].strip()
                
                elif linea.startswith("Threads:"):
                    datos["threads"] = int(linea.split(":")[1].strip())
                    
    except FileNotFoundError:
        return {"error": "El proceso murió antes de poder leerlo"}
    except Exception as e:
        return {"error": f"Error inesperado: {e}"}
        
    return datos

if __name__ == "__main__":
    # os.getpid() nos da el número de nuestro propio script de Python
    mi_pid = os.getpid()

    resultado = obtener_datos_basicos(mi_pid)

    for clave, valor in resultado.items():
        #print(f" - {clave.capitalize()}: {valor}")