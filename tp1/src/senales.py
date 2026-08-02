import signal
import os
import fcntl

# 1. Creamos un pipe del sistema operativo
pipe_r, pipe_w = os.pipe()

# 2. Configuramos el extremo de escritura para que sea no bloqueante
flags = fcntl.fcntl(pipe_w, fcntl.F_GETFL)
fcntl.fcntl(pipe_w, fcntl.F_SETFL, flags | os.O_NONBLOCK)

# 3. Le decimos a Python: "Cuando recibas una señal, escribí su número en este pipe"
signal.set_wakeup_fd(pipe_w)

def manejador_vacio(signum, frame):
    
    pass

def configurar_senales():
    """Registra las señales obligatorias del TP."""
    signal.signal(signal.SIGINT, manejador_vacio)   # Ctrl+C
    signal.signal(signal.SIGTERM, manejador_vacio)  # Apagado limpio
    signal.signal(signal.SIGHUP, manejador_vacio)   # Recargar config
    signal.signal(signal.SIGUSR1, manejador_vacio)  # Volcar snapshot
    signal.signal(signal.SIGUSR2, manejador_vacio)  # Toggle verbose
    
    return pipe_r