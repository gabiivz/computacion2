#!/usr/bin/env python3
"""Banco con cuentas en memoria compartida y registro de transacciones."""
from multiprocessing import Process, Array
import random
import time
import os

NUM_CUENTAS = 5
SALDO_INICIAL = 1000
NUM_PROCESOS = 3
TRANSFERENCIAS_POR_PROCESO = 10000  # <- Aumentado a 10.000 para forzar el fallo

def mostrar_saldos(cuentas, etiqueta):
    saldos = [cuentas[i] for i in range(NUM_CUENTAS)]
    total = sum(saldos)
    print(f"[{etiqueta}] Saldos: {saldos} | Total: {total}")

def cajero(cuentas, cajero_id, num_transferencias):
    """Un cajero que realiza transferencias entre cuentas."""
    for _ in range(num_transferencias):
        origen = random.randint(0, NUM_CUENTAS - 1)
        destino = random.randint(0, NUM_CUENTAS - 1)
        while destino == origen:
            destino = random.randint(0, NUM_CUENTAS - 1)

        monto = random.randint(1, 50)

        if cuentas[origen] >= monto:
            # Race condition inminente:
            cuentas[origen] -= monto
            cuentas[destino] += monto

            # --- NUEVO: Log de transferencias ---
            # Cada cajero anota lo que acaba de hacer en un archivo
            with open("historial_transferencias.txt", "a") as f:
                f.write(f"Cajero {cajero_id} transfirió ${monto} de la Cuenta {origen} a la Cuenta {destino}\n")

    print(f"[Cajero {cajero_id}] Completó {num_transferencias} transferencias")

if __name__ == '__main__':
    # (El resto del código del main queda exactamente igual)
    # Limpiamos el archivo de log anterior si existe
    if os.path.exists("historial_transferencias.txt"):
        os.remove("historial_transferencias.txt")
        
    cuentas = Array('i', [SALDO_INICIAL] * NUM_CUENTAS)
    print(f"=== Banco con {NUM_CUENTAS} cuentas ===")
    print(f"=== Saldo total esperado: {NUM_CUENTAS * SALDO_INICIAL} ===\n")
    
    mostrar_saldos(cuentas, "INICIO")
    
    procesos = []
    for i in range(NUM_PROCESOS):
        p = Process(target=cajero, args=(cuentas, i, TRANSFERENCIAS_POR_PROCESO))
        p.start()
        procesos.append(p)
        
    for p in procesos:
        p.join()
        
    mostrar_saldos(cuentas, "FINAL")
    
    total_final = sum(cuentas[i] for i in range(NUM_CUENTAS))
    total_esperado = NUM_CUENTAS * SALDO_INICIAL
    
    if total_final != total_esperado:
        print(f"\n¡ERROR! Diferencia detectada: ${abs(total_esperado - total_final)}")
        print("Esto es una race condition - se necesita sincronización")
    else:
        print(f"\nTodo correcto (pero fue suerte - ejecutalo varias veces)")