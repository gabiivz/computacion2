import os

def archivo_existe(path):
    pid = os.fork()
    if pid == 0:
        try:
            with open(path):
                pass
            os._exit(0)
        except OSError:
            os._exit(1)
    else:
        _, status = os.waitpid(pid, 0)
        return os.WEXITSTATUS(status) == 0

print(archivo_existe("/etc/passwd"))     # True
print(archivo_existe("/no_existe"))      # False