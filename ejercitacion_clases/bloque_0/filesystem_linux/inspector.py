import os
import sys
import stat
import pwd
import grp
from datetime import datetime
from pathlib import Path

# 1. Verificamos que el usuario pase un archivo
if len(sys.argv) < 2:
    print("Uso: python3 inspector.py <ruta>")
    sys.exit(1)

ruta = sys.argv[1]
p = Path(ruta)

# 2. Obtenemos la información del inodo
try:
    info = p.lstat()
except FileNotFoundError:
    print("Error: El archivo no existe.")
    sys.exit(1)

# 3. Empezamos a mostrar la info
print(f"Archivo: {ruta}")

# Tipo
if p.is_symlink(): tipo = f"enlace simbólico -> {os.readlink(p)}"
elif p.is_dir(): tipo = "directorio"
else: tipo = "archivo regular"
print(f"Tipo: {tipo}")

# Tamaño
print(f"Tamaño: {info.st_size} bytes")

# Permisos
letras = stat.filemode(info.st_mode)
octal = oct(info.st_mode & 0o777)[2:]
print(f"Permisos: {letras} ({octal})")

# Dueño y Grupo
user = pwd.getpwuid(info.st_uid).pw_name
group = grp.getgrgid(info.st_gid).gr_name
print(f"Propietario: {user} (uid: {info.st_uid})")
print(f"Grupo: {group} (gid: {info.st_gid})")

# Inodo y Enlaces
print(f"Inodo: {info.st_ino}")
print(f"Enlaces duros: {info.st_nlink}")

# Tiempo (Modificación)
fecha = datetime.fromtimestamp(info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
print(f"Última modificación: {fecha}")
acceso = datetime.fromtimestamp(info.st_atime).strftime('%Y-%m-%d %H:%M:%S')
print(f"Último acceso: {acceso}")
# Contenido (si es directorio)
if p.is_dir():
    try:
        # Listamos el contenido y contamos cuántos hay
        elementos = list(p.iterdir())
        print(f"Contenido: {len(elementos)} elementos")
    except PermissionError:
        print("Contenido: [Sin permiso para leer el directorio]")