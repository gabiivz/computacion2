import sys

def main():
    numeros = sys.argv[1:]
    suma = 0
    for num in numeros:
        try:
            suma += float(num)
        except ValueError:
            print(f'Error: "{num}" no es un número válido.')
            sys.exit(1)
    print(f'La suma de los números es: {suma}')

if __name__ == '__main__':
    main()