import os
import sys
import platform

print("Sintesis del sistema:")
#version de python
print(f"Python: {sys.version}")
#so 
print(f"Sistema: {platform.system()} {platform.release()}")
#cant cpus
print(f"CPUs: {os.cpu_count()}")
#memoria disponible
try:
    with open('/proc/meminfo', 'r') as f:
        for line in f:
            if 'MemTotal' in line:
                print(f"Memoria Total: {line.split()[1]} KB")
                break
except FileNotFoundError:
    print("Memoria: No se pudo obtener (no es un sistema Linux)")
#variables de entorno python
print("Variables de entorno relacionadas con Python:")
print("Variables de entorno PYTHON:")
python_vars = {k: v for k, v in os.environ.items() if k.startswith("PYTHON")}
if python_vars:
    for k, v in python_vars.items():
        print(f"   {k}: {v}")
else:
    print("   (Ninguna variable encontrada)")