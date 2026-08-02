#!/usr/bin/env python3
"""Cálculo paralelo de senos usando Array y Value compartidos."""
from multiprocessing import Process, Array, Value
import math

def calcular_seno(resultado, suma_total, inicio, fin):
    """Calcula el seno de i * 0.01 y lo acumula en el total compartido."""
    for i in range(inicio, fin):
        valor = math.sin(i * 0.01)
        resultado[i] = valor
        
        # BONUS: Suma directa sobre el Value compartido
        # ¡Peligro! Acá es donde ocurre la Race Condition
        suma_total.value += valor

if __name__ == '__main__':
    TAMAÑO = 100
    NUM_PROCESOS = 4
    
    # 1. Creamos un Array compartido de 100 'doubles' (números con coma)
    resultado = Array('d', TAMAÑO)
    
    # 2. Creamos un Value compartido para la suma, inicializado en 0.0
    suma_total = Value('d', 0.0)
    
    # 3. Dividimos el trabajo
    chunk = TAMAÑO // NUM_PROCESOS
    procesos = []
    
    print("=== Lanzando procesos ===")
    for i in range(NUM_PROCESOS):
        ini = i * chunk
        fin = (i + 1) * chunk if i < NUM_PROCESOS - 1 else TAMAÑO
        
        # Le pasamos nuestras estructuras compartidas como argumentos
        p = Process(target=calcular_seno, args=(resultado, suma_total, ini, fin))
        p.start()
        procesos.append(p)
        
    # 4. El padre espera a todos
    for p in procesos:
        p.join()
        
    # 5. Mostrar los primeros 20 resultados
    print("\n=== Primeros 20 resultados ===")
    for i in range(20):
        print(f"resultado[{i}] = {resultado[i]:.6f}")
        
    # 6. Análisis del BONUS (Race Condition)
    print("\n=== Análisis de Race Condition ===")
    
    # Calculamos la suma real en el proceso padre para comparar
    suma_real = sum(math.sin(i * 0.01) for i in range(TAMAÑO))
    
    print(f"Suma acumulada por los procesos (Value): {suma_total.value:.6f}")
    print(f"Suma matemática real esperada:           {suma_real:.6f}")
    
    if abs(suma_total.value - suma_real) > 1e-9:
        print("\n⚠️ ¡Race condition detectada! Los valores NO coinciden.")
        print("Varios procesos intentaron leer y escribir 'suma_total.value' al mismo tiempo y se pisaron los datos.")
    else:
        print("\n✅ Los valores coinciden.")
        print("Nota: Si no hubo race condition, fue por pura suerte (son muy pocos números y los procesos no llegaron a cruzarse). En un array más grande, fallará seguro sin un Lock.")