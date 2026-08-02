#!/usr/bin/env python3
"""Usar mmap como almacenamiento binario estructurado para registros."""
import mmap
import struct
import os

ARCHIVO = "/tmp/registros.bin"
NUM_ELEMENTOS = 5

# Definimos el formato del registro: 'i' (entero, 4 bytes) + 'f' (float, 4 bytes) + '20s' (20 caracteres/bytes)
FORMATO = 'i f 20s' 

# Dejamos que Python calcule automáticamente cuántos bytes ocupa en total este formato
TAMAÑO_REGISTRO = struct.calcsize(FORMATO) 
TAMAÑO_TOTAL = NUM_ELEMENTOS * TAMAÑO_REGISTRO

# 1. Crear el archivo con el tamaño exacto que necesitamos
with open(ARCHIVO, "wb") as f:
    f.write(b'\x00' * TAMAÑO_TOTAL)

with open(ARCHIVO, "r+b") as f:
    mm = mmap.mmap(f.fileno(), TAMAÑO_TOTAL)

    # Nombres de ejemplo para nuestros 5 registros
    nombres_alumnos = ["Ana", "Beto", "Carlos", "Diana", "Elena"]

    # 2. Escribir los registros
    print("Escribiendo registros en memoria...")
    for i in range(NUM_ELEMENTOS):
        identificador = i + 1
        nota = 7.5 + (i * 0.5)  # Notas inventadas: 7.5, 8.0, 8.5...
        
        # PREPARAR EL TEXTO:
        # struct necesita exactamente 20 bytes. .encode() lo pasa a bytes, y .ljust(20, b'\x00') 
        # le agrega caracteres nulos al final hasta completar los 20 espacios obligatorios.
        nombre_bytes = nombres_alumnos[i].encode('utf-8').ljust(20, b'\x00')
        
        # El offset indica en qué byte exacto arranca este registro
        offset = i * TAMAÑO_REGISTRO
        
        # Empaquetamos los 3 datos juntos
        struct.pack_into(FORMATO, mm, offset, identificador, nota, nombre_bytes)
        print(f"  -> Guardado en pos {i}: ID={identificador}, Nota={nota}, Nombre={nombres_alumnos[i]}")

    # 3. Leer todos los registros
    print("\nLeyendo registros desde memoria...")
    for i in range(NUM_ELEMENTOS):
        offset = i * TAMAÑO_REGISTRO
        
        # unpack_from devuelve una tupla con los 3 valores
        identificador, nota, nombre_bytes = struct.unpack_from(FORMATO, mm, offset)
        
        # LIMPIAR EL TEXTO:
        # Leemos los bytes, quitamos la basura (los caracteres nulos del final con rstrip) y pasamos a string
        nombre = nombre_bytes.decode('utf-8').rstrip('\x00')
        
        # Usamos :.2f para que la nota se imprima con 2 decimales y quede prolijo
        print(f"  <- Leído de pos {i}: ID={identificador}, Nota={nota:.2f}, Nombre={nombre}")

    mm.close()

# Borramos el archivo temporal para no dejar basura en el sistema
os.unlink(ARCHIVO)