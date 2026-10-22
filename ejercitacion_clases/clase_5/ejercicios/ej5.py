#!/usr/bin/env python3
"""Mini-shell con redirección."""
import os
import sys

def parsear_linea(linea):
    partes = linea.split()
    comando = partes[0] if partes else None
    args = []
    archivo_salida = None
    archivo_entrada = None
    es_append = False  # <--- NUEVA BANDERA

    i = 1
    while i < len(partes):
        # Chequeamos '>>' PRIMERO porque tiene dos caracteres
        if partes[i] == ">>":
            archivo_salida = partes[i + 1]
            es_append = True
            i += 2
        elif partes[i] == ">":
            archivo_salida = partes[i + 1]
            es_append = False
            i += 2
        elif partes[i] == "<":
            archivo_entrada = partes[i + 1]
            i += 2
        else:
            args.append(partes[i])
            i += 1

    return comando, args, archivo_salida, archivo_entrada, es_append # Devolvemos la bandera


def ejecutar(comando, args, archivo_salida=None, archivo_entrada=None, es_append=False):
    pid = os.fork()

    if pid == 0:
        if archivo_salida:
            # Armamos las banderas base
            flags = os.O_CREAT | os.O_WRONLY
            
            # Decidimos si truncamos (borramos) o hacemos append (agregamos al final)
            if es_append:
                flags |= os.O_APPEND
            else:
                flags |= os.O_TRUNC
                
            fd = os.open(archivo_salida, flags, 0o644)
            os.dup2(fd, 1)
            os.close(fd)

        if archivo_entrada:
            fd = os.open(archivo_entrada, os.O_RDONLY)
            os.dup2(fd, 0)
            os.close(fd)

        try:
            os.execvp(comando, [comando] + args)
        except OSError as e:
            print(f"Error: {e}", file=sys.stderr)
            os._exit(127)

    else:
        _, status = os.wait()
        return os.WEXITSTATUS(status)

def main():
    while True:
        try:
            linea = input("minish$ ")
        except EOFError:
            print("\nChau!")
            break

        linea = linea.strip()
        if not linea:
            continue

        if linea == "exit":
            break
        comando, args, salida, entrada, es_append = parsear_linea(linea)
        
        if comando:
            ejecutar(comando, args, salida, entrada, es_append)

if __name__ == "__main__":
    main()