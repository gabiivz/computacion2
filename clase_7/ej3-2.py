#!/usr/bin/env python3
"""Varios hijos calculan sumas parciales y las escriben en regiones separadas del mmap."""
import mmap
import os
import struct

NUM_HIJOS = 4
# Ahora solo necesitamos guardar UN entero (la suma parcial) por hijo. 
# El formato 'i' ocupa 4 bytes, así que reducimos el tamaño de la región.
TAMAÑO_POR_HIJO = 4 
TAMAÑO_TOTAL = NUM_HIJOS * TAMAÑO_POR_HIJO

MAX_NUM = 100  # Vamos a sumar del 1 al 100
RANGO_POR_HIJO = MAX_NUM // NUM_HIJOS # 100 / 4 = 25 números por hijo

# mmap anónimo (-1): Esto crea memoria compartida directo en la RAM, sin crear un archivo físico.
mm = mmap.mmap(-1, TAMAÑO_TOTAL)

hijos = []

print("=== Lanzando procesos trabajadores ===")
for i in range(NUM_HIJOS):
    pid = os.fork()
    if pid == 0:
        # ----------------------------------------------------
        # HIJO: Trabaja en su porción del problema
        # ----------------------------------------------------
        offset = i * TAMAÑO_POR_HIJO
        
        # 1. Calcular de dónde a dónde le toca sumar
        inicio = (i * RANGO_POR_HIJO) + 1
        fin = (i + 1) * RANGO_POR_HIJO
        
        # 2. Hacer el trabajo pesado (sumar los números en su rango)
        suma_parcial = sum(range(inicio, fin + 1))
        
        print(f"[Hijo {i}] PID {os.getpid()}: Sumando del {inicio} al {fin} -> Parcial: {suma_parcial}")
        
        # 3. Escribir el resultado en su región exacta del mapa de memoria
        struct.pack_into('i', mm, offset, suma_parcial)
        
        # El hijo muere acá, no sin antes dejar su legado en la memoria
        os._exit(0)
    else:
        hijos.append(pid)

# ----------------------------------------------------
# PADRE: Espera y recolecta
# ----------------------------------------------------
# El padre hace una pausa y espera a que TODOS los hijos terminen
for pid in hijos:
    os.waitpid(pid, 0)

print("\n=== Padre consolidando resultados ===")
suma_total = 0

# Leer los resultados parciales de la memoria compartida
for i in range(NUM_HIJOS):
    offset = i * TAMAÑO_POR_HIJO
    
    # Desempaquetar el entero que dejó el hijo 'i'
    suma_parcial = struct.unpack_from('i', mm, offset)[0]
    
    print(f"  Región {i} leída -> Aportó: {suma_parcial}")
    suma_total += suma_parcial

# Comprobación matemática (Fórmula de Gauss: n * (n + 1) / 2)
suma_matematica_esperada = MAX_NUM * (MAX_NUM + 1) // 2

print("\n=== Resultado Final ===")
print(f"Suma total calculada por los hijos: {suma_total}")
print(f"Suma esperada matemáticamente: {suma_matematica_esperada}")

# Liberar la memoria
mm.close()