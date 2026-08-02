import os
import time

def analizar_fds(pid):
    """
    Lee /proc/<pid>/fd y extrae el destino de cada File Descriptor.
    """
    ruta_fd = f"/proc/{pid}/fd"
    lista_fds = []

    try:
        # os.listdir nos da los números de los FDs (0, 1, 2, 3...)
        for fd in os.listdir(ruta_fd):
            ruta_absoluta = os.path.join(ruta_fd, fd)
            try:
                # readlink nos dice a dónde apunta realmente ese FD
                destino = os.readlink(ruta_absoluta)
                
                # Inferimos el tipo de archivo mirando el nombre del destino
                if destino.startswith("pipe:"):
                    tipo = "PIPE"
                elif destino.startswith("socket:"):
                    tipo = "SOCKET"
                elif destino.startswith("/dev/"):
                    tipo = "DISPOSITIVO" 
                elif destino.startswith("anon_inode:"):
                    tipo = "INODO_ANONIMO" 
                else:
                    tipo = "ARCHIVO" 

                lista_fds.append({
                    "fd": fd,
                    "tipo": tipo,
                    "destino": destino
                })
            except (FileNotFoundError, PermissionError):
                continue
                
        return lista_fds
    except (FileNotFoundError, PermissionError):
        # El proceso entero murió o no tenemos permisos 
        return None

def fds_worker(snapshot, intervalo_compartido, seguir_corriendo):
    """
    Analizador que procesa la vista de File Descriptors.

    """
    
    while seguir_corriendo.value:
        try:
            pids_actuales = snapshot.get('pids_activos', [])
            diccionario_fds = {}
            
            for pid in pids_actuales:
                datos = analizar_fds(pid)
                if datos is not None:
                    diccionario_fds[pid] = datos
            
            # Subimos la info al Snapshot Global
            snapshot['fds'] = diccionario_fds
            
            time.sleep(intervalo_compartido.value)
            
        except KeyboardInterrupt:
            break
