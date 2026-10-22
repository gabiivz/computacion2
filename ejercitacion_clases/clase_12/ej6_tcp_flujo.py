"""Clase 12 - Ej 6 (obligatorio): TCP es un flujo de bytes, UDP preserva datagramas."""
import socket
import threading
import time


def tcp(pausa):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen()
    puerto = srv.getsockname()[1]
    lecturas = []

    def servidor():
        conn, _ = srv.accept()
        time.sleep(0.3 if not pausa else 0)  # sin pausa del cliente, dejamos que se acumule todo
        while (d := conn.recv(4096)):
            lecturas.append(d)
        conn.close()

    t = threading.Thread(target=servidor)
    t.start()
    c = socket.create_connection(("127.0.0.1", puerto))
    for msg in (b"HOLA", b"COMO", b"ESTAS"):
        c.send(msg)
        if pausa:
            time.sleep(0.5)
    c.close()
    t.join()
    srv.close()
    return lecturas


def udp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    s.settimeout(1)
    for msg in (b"HOLA", b"COMO", b"ESTAS"):
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(msg, s.getsockname())
    out = []
    try:
        while True:
            out.append(s.recvfrom(4096)[0])
    except socket.timeout:
        pass
    return out


if __name__ == "__main__":
    print("TCP sin pausa   :", tcp(pausa=False))
    print("TCP con pausa 1s:", tcp(pausa=True))
    print("UDP             :", udp())
