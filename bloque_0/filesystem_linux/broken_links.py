import argparse
import sys
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Detecta y limpia enlaces simbólicos rotos")
    parser.add_argument("directorio", help="Directorio donde buscar")
    parser.add_argument("--delete", action="store_true", help="Borrar los enlaces encontrados")
    parser.add_argument("--quiet", action="store_true", help="Solo mostrar el número de enlaces rotos")

    args = parser.parse_args()
    ruta_base = Path(args.directorio)

    if not ruta_base.is_dir():
        if not args.quiet:
            print(f"Error: '{args.directorio}' no es un directorio.")
        sys.exit(1)

    contador_rotos = 0

    # rglob("*") recorre todo el árbol de directorios
    for item in ruta_base.rglob("*"):
        try:
            # Lógica de la teoría: Es un link PERO no existe su destino
            if item.is_symlink() and not item.exists():
                contador_rotos += 1
                destino = os.readlink(item)

                if not args.quiet:
                    print(f"Enlace roto: {item} -> {destino} (no existe)")

                    if args.delete:
                        confirmar = input(f"  ¿Borrar {item.name}? [s/N]: ")
                        if confirmar.lower() == 's':
                            item.unlink()
                            print("  Borrado.")

        except PermissionError:
            continue

    # Resultado final
    if args.quiet:
        print(contador_rotos)
    else:
        print(f"\nTotal: {contador_rotos} enlaces rotos encontrados.")

if __name__ == "__main__":
    main()