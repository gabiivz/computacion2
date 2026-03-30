import sys

def main():
    #sys.argv[0] es saludo.py, los argumentos empiezan desde sys.argv[1]
    args = sys.argv[1:]
    if not args:
        print(f'Uso: {sys.argv[0]} <nombre>')
        sys.exit(1)
    #unimos args por si nombre tiene espacios
    nombre = ' '.join(args)
    print(f'Hola, {nombre}!')

if __name__ == '__main__':
    main()
