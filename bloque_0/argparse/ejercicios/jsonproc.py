"""Herramienta para inspeccionar y manipular JSON desde la terminal."""

import argparse
import sys
import json

def obtener_valor(data, path):
    """Navega el JSON usando notación de puntos (ej: productos.0.precio)."""
    keys = path.split('.')
    for key in keys:
        if isinstance(data, list):
            data = data[int(key)] # Si es lista, la clave es un índice
        else:
            data = data[key]
    return data

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", help="Archivo JSON o '-' para stdin")
    parser.add_argument("--keys", action="store_true", help="Listar claves de primer nivel")
    parser.add_argument("--get", help="Obtener valor por path (ej: usuario.nombre)")
    parser.add_argument("--pretty", action="store_true", help="Formatear con indentación")
    parser.add_argument("-o", "--output", type=argparse.FileType('w'), default=sys.stdout)

    args = parser.parse_args()

    # Cargar datos (de archivo o stdin)
    try:
    if args.archivo == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.archivo, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: El archivo '{args.archivo}' no existe.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: El archivo '{args.archivo}' no es un JSON válido.")
        sys.exit(1)

    # Lógica de acciones
    if args.keys:
        for k in data.keys():
            print(k)
    
    elif args.get:
        resultado = obtener_valor(data, args.get)
        print(json.dumps(resultado, ensure_ascii=False))

    elif args.pretty:
        json.dump(data, args.output, indent=4, ensure_ascii=False)
        print() # Nueva línea al final

if __name__ == "__main__":
    main()