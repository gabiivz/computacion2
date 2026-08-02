import os
import time
import signal

def watcher():
    archivo_vigilado = "archivo_prueba.txt"
    
    # 1. Creamos un archivo vacío para poder vigilarlo
    with open(archivo_vigilado, "w") as f:
        f.write("Estado inicial\n")

    pid = os.fork()

    if pid == 0:
        # HIJO: Se encarga exclusivamente del Polling
        print(f"[Hijo PID {os.getpid()}] Ojos en el archivo '{archivo_vigilado}'...")
        
        # Guardamos la fecha/hora exacta de la última modificación
        ultima_modificacion = os.path.getmtime(archivo_vigilado)
        
        while True:
            # Verificamos la fecha de modificación actual
            mod_actual = os.path.getmtime(archivo_vigilado)
            
            if mod_actual != ultima_modificacion:
                print(f"[Hijo] ¡Alerta! El archivo fue modificado.")
                ultima_modificacion = mod_actual # Actualizamos para el próximo chequeo
            
            # Polling: dormimos 1 segundo para no fundir el procesador chequeando
            time.sleep(1) 
            
    else:
        # PADRE: Controla el tiempo y manda la señal de muerte
        print(f"[Padre] Dejando al hijo vigilar. Le doy 8 segundos de vida...")
        
        # Simulamos que alguien (el padre en este caso) modifica el archivo a los 3 segundos
        time.sleep(3)
        with open(archivo_vigilado, "a") as f:
            f.write("¡Nueva línea de texto!\n")
        
        # Esperamos el resto del tiempo (5 segundos más)
        time.sleep(5)
        
        print("[Padre] Se acabó el tiempo. Matando al proceso hijo...")
        
        # MAGIA: Enviamos la señal SIGTERM (Signal Terminate) al PID del hijo
        os.kill(pid, signal.SIGTERM)
        
        # Recogemos el cadáver (proceso zombie) para dejar la memoria limpia
        os.wait()
        print("[Padre] Hijo eliminado correctamente. Fin del programa.")
        
        # Borramos el archivo de prueba
        os.remove(archivo_vigilado)

if __name__ == "__main__":
    watcher()