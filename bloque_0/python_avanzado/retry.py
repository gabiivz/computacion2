import time
import random
from functools import wraps
from typing import Callable, Any, Tuple, Type

def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: Tuple[Type[Exception], ...] = (Exception,)) -> Callable:
    
    # Manejo de casos borde (Argumentos inválidos)
    if max_attempts < 1:
        raise ValueError("max_attempts debe ser al menos 1.")
    if delay < 0:
        raise ValueError("delay no puede ser un número negativo.")

    def decorador(funcion: Callable) -> Callable:
        @wraps(funcion)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for intento in range(1, max_attempts + 1):
                try:
                    return funcion(*args, **kwargs)
                except exceptions as e:
                    if intento == max_attempts:
                        print(f"Intento {intento}/{max_attempts} falló: {e}. No hay más reintentos.")
                        raise
                    
                    print(f"Intento {intento}/{max_attempts} falló: {e}. Esperando {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorador

#ejemplos de uso
if __name__ == "__main__":
    
    print("=== TEST 1: Uso normal (falla aleatoria) ===")
    @retry(max_attempts=3, delay=0.5, exceptions=(ConnectionError,))
    def conectar_servidor() -> str:
        """Simula una conexión que falla el 70% de las veces."""
        if random.random() < 0.7:
            raise ConnectionError("Servidor no disponible")
        return "Conectado exitosamente"

    try:
        print(conectar_servidor())
    except ConnectionError:
        print("El servidor falló las 3 veces seguidas.")

    print("\n=== TEST 2: Manejo de Casos Borde (Argumentos inválidos) ===")
    try:
        # Intentamos configurar un decorador con intentos negativos
        @retry(max_attempts=0)
        def funcion_rota() -> None:
            pass
    except ValueError as e:
        print(f"Validación exitosa del decorador: {e}")