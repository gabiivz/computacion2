import os

pid = os.getpid()
print(f"PID: {pid}")
print(f"PPID: {os.getppid()}")
print(f"CWD: {os.getcwd()}")

print("\nFile descriptors abiertos:")
for fd in os.listdir(f"/proc/{pid}/fd"):
    try:
        link = os.readlink(f"/proc/{pid}/fd/{fd}")
        print(f"  fd {fd} -> {link}")
    except OSError:
        pass

print("\nMapa de memoria (primeras 20 líneas):")
with open(f"/proc/{pid}/maps") as f:
    for i, line in enumerate(f):
        if i >= 20: break
        print(f"  {line.strip()}")

#ej 2: Este proceso es el ancestro de todos los demás. Cada vez que abrís una terminal, systemd (o algún descendiente suyo) crea un proceso shell. Cuando en ese shell escribís un comando, el shell crea un proceso hijo para ejecutarlo.