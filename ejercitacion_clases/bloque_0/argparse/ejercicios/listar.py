#!/usr/bin/env python3
"""Listador de archivos estilo ls simplificado."""

import argparse
import sys
from pathlib import Path

def crear_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    # Argumento posicional OPCIONAL (default: directorio actual '.')
    parser.add_argument("directorio", nargs="?", default=".", help="Directorio a listar")
    
    # Flag para archivos ocultos
    parser.add_argument("-a", "--all", action="store_true", help="Incluir archivos ocultos")
    
    # Opción para filtrar por extensión
    parser.add_argument("--extension", help="Filtrar por extensión (ej: .py)")
    
    return parser

def main():
    parser = crear_parser()
    args = parser.parse_args()
    
    path = Path(args.directorio)
    
    if not path.exists():
        print(f"Error: El directorio '{args.directorio}' no existe.", file=sys.stderr)
        sys.exit(1)

    try:
        # iterdir() es el equivalente a os.listdir() pero devuelve objetos Path
        for item in path.iterdir():
            # 1. Filtro de archivos ocultos
            if not args.all and item.name.startswith("."):
                continue
                
            # 2. Filtro de extensión
            if args.extension and item.suffix != args.extension:
                continue
            
            # 3. Formateo (agregar / si es directorio)
            nombre = item.name
            if item.is_dir():
                nombre += "/"
                
            print(nombre)
            
    except PermissionError:
        print(f"Error: Sin permisos para acceder a '{args.directorio}'", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()