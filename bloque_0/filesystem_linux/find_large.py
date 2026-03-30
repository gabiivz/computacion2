#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

# 1. Función auxiliar: Siempre fuera del main para que sea prolijo
def parsear_tamano(texto):
    """Convierte '1M' a 1048576 bytes."""
    unidades = {'K': 1024, 'M': 1024**2, 'G': 1024**3}
    letra = texto[-1].upper() # Sacamos la última letra (K, M o G)
    
    if letra in unidades:
        try:
            numero = float(texto[:-1]) # El resto del texto es el número
            return int(numero * unidades[letra])
        except ValueError:
            print(f"Error: '{texto}' no es un tamaño válido.")
            sys.exit(1)
            
    return int(texto) # Si no tiene letra, asumimos que ya son bytes

# 2. Función principal
def main():
    parser = argparse.ArgumentParser(description="Busca archivos grandes en un directorio.")
    parser.add_argument("directorio", help="Carpeta donde empezar a buscar")
    parser.add_argument("--min-size", default="0", help="Tamaño mínimo (ej: 1M, 500K)")
    parser.add_argument("--top", type=int, help="Mostrar solo los N más grandes")

    args = parser.parse_args()
    
    # Usamos la función que definimos arriba
    min_bytes = parsear_tamano(args.min_size)
    ruta_base = Path(args.directorio)
    
    if not ruta_base.is_dir():
        print(f"Error: '{args.directorio}' no es un directorio válido.")
        sys.exit(1)

    encontrados = []

    # rglob("*") busca de forma recursiva (dentro de subcarpetas)
    for archivo in ruta_base.rglob("*"):
        try:
            if archivo.is_file():
                tamano = archivo.stat().st_size
                if tamano >= min_bytes:
                    encontrados.append((archivo, tamano))
        except PermissionError:
            continue # Ignoramos archivos donde no tenemos permiso

    # Lógica del TOP N
    if args.top:
        encontrados.sort(key=lambda x: x[1], reverse=True)
        encontrados = encontrados[:args.top]
        print(f"--- Los {len(encontrados)} archivos más grandes ---")

    # Mostrar resultados finales
    total_bytes = 0
    for item, tam in encontrados:
        # Mostramos la ruta relativa para que no sea tan largo el texto
        print(f"{item} ({tam / (1024**2):.2f} MB)")
        total_bytes += tam

    print(f"\nTotal: {len(encontrados)} archivos encontrados.")
    print(f"Espacio total ocupado: {total_bytes / (1024**2):.2f} MB")

if __name__ == "__main__":
    main()