import os
import sys
# Importar readline habilita mágicamente el historial con las flechas arriba/abajo en el input()
import readline 

def shell_simple():
    while True:
        # 1. Mostrar prompt y leer comando
        try:
            linea = input("$ ")
        except EOFError:
            break

        if not linea.strip():
            continue

        # --- EXTENSIÓN: Background processes con & ---
        background = False
        if linea.strip().endswith("&"):
            background = True
            linea = linea.strip()[:-1] # Le quitamos el '&' al comando

        if not linea.strip():
            continue

        # --- EXTENSIÓN: Manejo de pipes con | ---
        if "|" in linea:
            comandos_pipe = linea.split("|")
            if len(comandos_pipe) == 2:
                cmd1 = comandos_pipe[0].strip().split()
                cmd2 = comandos_pipe[1].strip().split()
                
                # Creamos el túnel (pipe)
                r, w = os.pipe()
                
                pid1 = os.fork()
                if pid1 == 0:
                    # Hijo 1: conecta su salida estándar (stdout) a la entrada del pipe (w)
                    os.close(r)
                    os.dup2(w, sys.stdout.fileno())
                    os.close(w)
                    try:
                        os.execvp(cmd1[0], cmd1)
                    except OSError as e:
                        print(f"{cmd1[0]}: {e}")
                        os._exit(1)
                
                pid2 = os.fork()
                if pid2 == 0:
                    # Hijo 2: conecta su entrada estándar (stdin) a la salida del pipe (r)
                    os.close(w)
                    os.dup2(r, sys.stdin.fileno())
                    os.close(r)
                    try:
                        os.execvp(cmd2[0], cmd2)
                    except OSError as e:
                        print(f"{cmd2[0]}: {e}")
                        os._exit(1)
                
                # Padre: cierra los pipes para no quedarse colgado esperando y espera a los hijos
                os.close(r)
                os.close(w)
                if not background:
                    os.waitpid(pid1, 0)
                    _, status = os.waitpid(pid2, 0)
                    if os.WIFEXITED(status):
                        codigo = os.WEXITSTATUS(status)
                        if codigo != 0:
                            print(f"[Salió con código {codigo}]")
            else:
                print("Esta shell básica soporta solo un pipe (2 comandos) a la vez.")
            continue


        # Flujo normal para comandos sin pipe
        partes = linea.strip().split()
        comando = partes[0]
        args = partes[1:]

        # --- EXTENSIÓN: Variables de entorno con export ---
        if comando == "export":
            if args and "=" in args[0]:
                var, val = args[0].split("=", 1)
                os.environ[var] = val
            else:
                print("Uso: export VAR=value")
            continue

        # Comandos internos (no hacen fork)
        if comando == "exit":
            break
        if comando == "cd":
            try:
                os.chdir(args[0] if args else os.environ["HOME"])
            except OSError as e:
                print(f"cd: {e}")
            continue

        # Comandos externos: fork + exec
        pid = os.fork()

        if pid == 0:
            # Hijo: ejecutar el comando
            try:
                os.execvp(comando, [comando] + args)
            except OSError as e:
                print(f"{comando}: {e}")
                os._exit(1)
        else:
            # Padre: esperar al hijo (¡SOLO SI NO ES BACKGROUND!)
            if not background:
                _, status = os.wait()
                if os.WIFEXITED(status):
                    codigo = os.WEXITSTATUS(status)
                    if codigo != 0:
                        print(f"[Salió con código {codigo}]")
            else:
                print(f"[Corriendo en background - PID: {pid}]")

if __name__ == "__main__":
    shell_simple()