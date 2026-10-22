import sys
import os

def main():
    # 1. Validar que se haya pasado un argumento
    # sys.argv[0] es el script, sys.argv[1] debería ser el archivo
    if len(sys.argv) < 2:
        print("Error: No se ha especificado un archivo.")
        sys.exit(1)
    archivo = sys.argv[1]
    #hay que validar que el archivo exista
    if not os.path.isfile(archivo):
        print(f"Error: El archivo '{archivo}' no existe.")
        sys.exit(1)
    # 2. Contar líneas del archivo
    with open(archivo, 'r') as f:
        lineas = f.readlines()
        num_lineas = len(lineas)
    print(f"El archivo '{archivo}' tiene {num_lineas} líneas.")

if __name__ == '__main__':
    main()