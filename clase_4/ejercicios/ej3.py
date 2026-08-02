
import os
import sys

def lanzar(comando, args):
    pid = os.fork()
    if pid == 0:
        os.execvp(comando, [comando] + args)
        # Si llegamos aquí, exec falló
        print(f"Error: no se pudo ejecutar {comando}", file=sys.stderr)
        os._exit(127)
    else:
        _, status = os.waitpid(pid, 0)
        return os.WEXITSTATUS(status)

codigo = lanzar("ls", ["-la", "/tmp"])
print(f"Comando terminó con código {codigo}")