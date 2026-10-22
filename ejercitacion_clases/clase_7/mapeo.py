#!/usr/bin/env python3
"""Proceso que escribe en memoria compartida via archivo."""
import mmap
import struct
import time

ARCHIVO = "/tmp/compartido.bin"
TAMAÑO = 256

# Crear archivo
with open(ARCHIVO, "wb") as f:
    f.write(b'\x00' * TAMAÑO)

with open(ARCHIVO, "r+b") as f:
    mm = mmap.mmap(f.fileno(), TAMAÑO)

    tiempos = []
    for i in range(10):
        mensaje = f"Dato #{i}: {time.ctime()}".encode()

        t0 = time.perf_counter()
        mm.seek(0)
        # Primero escribir largo, después el mensaje
        mm.write(struct.pack('i', len(mensaje)))
        mm.write(mensaje)
        mm.flush()   # ← comentar/descomentar para comparar tiempos
        t1 = time.perf_counter()

        tiempos.append((t1 - t0) * 1_000_000)  # microsegundos
        print(f"[ESCRITOR] Escribí: {mensaje.decode()} ({tiempos[-1]:.1f} µs)")
        time.sleep(1)

    print(f"\nPromedio por escritura: {sum(tiempos)/len(tiempos):.1f} µs")
    mm.close()