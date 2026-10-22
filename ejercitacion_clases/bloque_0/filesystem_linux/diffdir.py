#!/usr/bin/env python3
import argparse
import sys
import hashlib
from pathlib import Path
from datetime import datetime

def calcular_hash(ruta_archivo):
    """Genera la huella digital del archivo leyendo su contenido."""
    sha256 = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        # Lee el archivo en pedacitos para no trabar la memoria
        for bloque in iter(lambda: f.read(4096), b""):
            sha256.update(bloque)
    return sha256.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Compara dos directorios.")
    parser.add_argument("dir1", help="Primer directorio")
    parser.add_argument("dir2", help="Segundo directorio")
    parser.add_argument("--recursive", action="store_true", help="Buscar dentro de subcarpetas")
    parser.add_argument("--checksum", action="store_true", help="Comparar contenido exacto con Hash")

    args = parser.parse_args()

    path1 = Path(args.dir1)
    path2 = Path(args.dir2)

    if not path1.is_dir() or not path2.is_dir():
        print("Error: Los dos argumentos deben ser carpetas válidas.")
        sys.exit(1)
    if args.recursive:
        arch1 = {str(f.relative_to(path1)): f for f in path1.rglob("*") if f.is_file()}
        arch2 = {str(f.relative_to(path2)): f for f in path2.rglob("*") if f.is_file()}
    else:
        arch1 = {f.name: f for f in path1.iterdir() if f.is_file()}
        arch2 = {f.name: f for f in path2.iterdir() if f.is_file()}
    nombres1 = set(arch1.keys())
    nombres2 = set(arch2.keys())

    print(f"Comparando {args.dir1} con {args.dir2}...\n")

    solo_en_1 = nombres1 - nombres2
    if solo_en_1:
        print(f"Solo en {args.dir1}:")
        for n in solo_en_1: print(f"  {n}")

    solo_en_2 = nombres2 - nombres1
    if solo_en_2:
        print(f"\nSolo en {args.dir2}:")
        for n in solo_en_2: print(f"  {n}")
    print("\nModificados:")
    identicos = 0
    comunes = nombres1 & nombres2

    for n in comunes:
        f1 = arch1[n]
        f2 = arch2[n]
        s1 = f1.stat()
        s2 = f2.stat()
        
        cambio = False
        if s1.st_size != s2.st_size:
            print(f"  {n} (Tamaño: {s1.st_size} -> {s2.st_size} bytes)")
            cambio = True
        elif abs(s1.st_mtime - s2.st_mtime) > 1:
            fecha1 = datetime.fromtimestamp(s1.st_mtime).strftime('%Y-%m-%d')
            fecha2 = datetime.fromtimestamp(s2.st_mtime).strftime('%Y-%m-%d')
            print(f"  {n} (Fecha: {fecha1} -> {fecha2})")
            cambio = True
        elif args.checksum:
            if calcular_hash(f1) != calcular_hash(f2):
                print(f"  {n} (Contenido diferente según el checksum)")
                cambio = True

        if not cambio:
            identicos += 1

    print(f"\nIdénticos: {identicos} archivos")

if __name__ == "__main__":
    main()