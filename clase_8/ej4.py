import multiprocessing
import time

def hijo(conn):
    for i in range(5):
        # Recibe mensaje del padre
        mensaje = conn.recv()
        print(f"[Hijo] Recibí: {mensaje}")
        time.sleep(0.5)
        # Responde al padre
        conn.send(f"Pong {i+1}")
    conn.close()

if __name__ == '__main__':
    # Creamos un pipe bidireccional
    padre_conn, hijo_conn = multiprocessing.Pipe()

    p = multiprocessing.Process(target=hijo, args=(hijo_conn,))
    p.start()

    for i in range(5):
        # Envía mensaje al hijo
        padre_conn.send(f"Ping {i+1}")
        # Recibe respuesta del hijo
        respuesta = padre_conn.recv()
        print(f"[Padre] Recibí: {respuesta}")

    p.join()
    padre_conn.close()