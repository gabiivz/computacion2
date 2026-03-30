import argparse

def main():
    parser = argparse.ArgumentParser(description='Convertir temperaturas entre Celsius y Fahrenheit.')
    parser.add_argument('valor', type=float, help='La temperatura a convertir')
    parser.add_argument('-t', '--to',
                        choices=['C', 'F'],
                        required=True,
                        help='La unidad a convertir (C para Celsius, F para Fahrenheit)')
    args = parser.parse_args()
    if args.to == 'F':
        resultado = (args.valor * 9/5) + 32
        print(f'{args.valor}°C es igual a {resultado:.2f}°F')
    else:
        resultado = (args.valor - 32) * 5/9
        print(f'{args.valor}°F es igual a {resultado:.2f}°C')

if __name__ == '__main__':
    main()