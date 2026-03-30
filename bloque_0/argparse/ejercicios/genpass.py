#!/usr/bin/env python3
"""Generador de contraseñas seguras para la terminal."""

import argparse
import sys
import secrets
import string

def crear_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--length", type=int, default=12, help="Longitud de la clave")
    parser.add_argument("--no-symbols", action="store_true", help="Excluir símbolos")
    parser.add_argument("--no-numbers", action="store_true", help="Excluir números")
    parser.add_argument("--count", type=int, default=1, help="Cantidad de claves a generar")
    return parser

def generar_una_clave(longitud, sin_simbolos, sin_numeros):
    # Definimos los "bloques" de construcción
    letras = string.ascii_letters
    numeros = string.digits
    simbolos = "!@#$%&"
    
    # Armamos el pool (la bolsa de caracteres) según las opciones
    pool = letras
    if not sin_numeros:
        pool += numeros
    if not sin_simbolos:
        pool += simbolos
        
    # Generamos la clave eligiendo caracteres al azar del pool
    return "".join(secrets.choice(pool) for _ in range(longitud))

def main():
    parser = crear_parser()
    args = parser.parse_args()

    # Validamos que la longitud sea razonable
    if args.length < 1:
        print("Error: La longitud debe ser mayor a 0", file=sys.stderr)
        sys.exit(1)

    try:
        for _ in range(args.count):
            print(generar_una_clave(args.length, args.no_symbols, args.no_numbers))
        sys.exit(0)
    except Exception as e:
        print(f"Error inesperado: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
    