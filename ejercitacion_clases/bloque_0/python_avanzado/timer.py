import time
from contextlib import contextmanager
from typing import Optional, Generator, Type, Any

class Timer:
    """
    Context manager que mide el tiempo de ejecución de un bloque de código.
    Permite acceder al tiempo transcurrido en vivo y al finalizar.
    """
    def __init__(self, nombre: Optional[str] = None) -> None:
        # Caso borde: validar que el nombre sea un string o None
        if nombre is not None and not isinstance(nombre, str):
            raise ValueError("El nombre del Timer debe ser un string.")
            
        self.nombre = nombre
        self.inicio: float = 0.0
        self.fin: Optional[float] = None

    def __enter__(self) -> 'Timer':
        """Inicia el cronómetro al entrar al bloque with."""
        self.inicio = time.time()
        return self

    @property
    def elapsed(self) -> float:
        """
        Calcula el tiempo transcurrido en segundos.
        Si el bloque ya terminó, devuelve el tiempo total.
        Si sigue corriendo, devuelve el tiempo actual en vivo.
        """
        if self.fin is not None:
            return self.fin - self.inicio
        return time.time() - self.inicio

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Any) -> bool:
        """Detiene el cronómetro e imprime el resultado si se asignó un nombre."""
        self.fin = time.time()
        if self.nombre is not None:
            print(f"[Timer] {self.nombre}: {self.elapsed:.3f}s")
        return False  # No silenciar posibles excepciones

class EstadoTimer:
    """Clase auxiliar para mantener el estado del timer en la versión decorador."""
    def __init__(self) -> None:
        self.inicio: float = time.time()
        self.fin: Optional[float] = None
        
    @property
    def elapsed(self) -> float:
        if self.fin is not None:
            return self.fin - self.inicio
        return time.time() - self.inicio

@contextmanager
def timer_decorador(nombre: Optional[str] = None) -> Generator[EstadoTimer, None, None]:
    """
    Context manager (vía generador) que mide el tiempo de ejecución.
    """
    # validar tipo de dato
    if nombre is not None and not isinstance(nombre, str):
        raise ValueError("El nombre del Timer debe ser un string.")
        
    estado = EstadoTimer()
    try:
        yield estado 
    finally:
        estado.fin = time.time()
        if nombre is not None:
            print(f"[Timer] {nombre}: {estado.elapsed:.3f}s")
#ejemplos de uso
if __name__ == "__main__":
    print("=== TEST 1: Con nombre (imprime solo al final) ===")
    with Timer("Procesamiento de datos"):
        _ = [x**2 for x in range(1000000)]
    
    print("\n=== TEST 2: Sin nombre (accediendo a elapsed afuera) ===")
    with Timer() as t:
        time.sleep(0.5)
    print(f"El bloque tardó {t.elapsed:.3f} segundos")
    
    print("\n=== TEST 3: Casos Borde (Error intencional) ===")
    try:
        with Timer(123):  # Pasamos un entero en vez de string
            pass
    except ValueError as e:
        print(f"Excepción atajada correctamente: {e}")