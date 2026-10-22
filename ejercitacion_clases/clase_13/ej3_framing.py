"""Clase 13 - Ej 3 (obligatorio): framing sobre TCP por delimitador y por longitud."""
import socket
import struct
import threading
import time


# ---------- Parte B: delimitador '\n' ----------
def recibir_lineas(sock):
    buffer = b""
    while True:
        pedazo = sock.recv(4096)
        if not pedazo:
            return
        buffer += pedazo
        while b"\n" in buffer:  # puede haber varias líneas completas en un solo recv()
            linea, buffer = buffer.split(b"\n", 1)
            yield linea


def atender_lineas(conn):
    with conn:
        for linea in recibir_lineas(conn):
            conn.sendall(linea.upper() + b"\n")


# ---------- Parte C: prefijo de longitud (4 bytes, big endian) ----------
def recibir_exacto(sock, n):
    """recv(n) puede devolver menos de n bytes: hay que insistir hasta completar."""
    partes = []
    faltan = n
    while faltan > 0:
        pedazo = sock.recv(faltan)
        if not pedazo:
            return None  # cerraron antes de completar
        partes.append(pedazo)
        faltan -= len(pedazo)
    return b"".join(partes)


MAX_MSG = 1 << 20  # 1 MiB: sin tope, un cliente podría pedirnos reservar 4 GB


def enviar_mensaje(sock, payload: bytes):
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def recibir_mensaje(sock):
    cab = recibir_exacto(sock, 4)
    if cab is None:
        return None
    (n,) = struct.unpack("!I", cab)
    if n > MAX_MSG:
        raise ValueError(f"mensaje demasiado grande: {n}")
    return recibir_exacto(sock, n) if n else b""


def atender_longitud(conn):
    with conn:
        while (msg := recibir_mensaje(conn)) is not None:
            enviar_mensaje(conn, msg.upper())


# ---------- pruebas ----------
def servidor(handler):
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen()

    def loop():
        conn, _ = srv.accept()
        handler(conn)
        srv.close()

    threading.Thread(target=loop, daemon=True).start()
    return srv.getsockname()[1]


def leer_n_lineas(sock, n):
    return list(__import__("itertools").islice(recibir_lineas(sock), n))


if __name__ == "__main__":
    # B.4 todo junto
    c = socket.create_connection(("127.0.0.1", servidor(atender_lineas)))
    c.sendall(b"uno\ndos\ntres\n")
    print("B todo junto     :", leer_n_lineas(c, 3))
    c.close()

    # B.5 byte por byte
    c = socket.create_connection(("127.0.0.1", servidor(atender_lineas)))
    for b in b"hola\n":
        c.sendall(bytes([b]))
        time.sleep(0.05)
    print("B byte por byte  :", leer_n_lineas(c, 1))
    c.close()

    # C: mensaje con '\n' adentro, vacío, y partido en pedacitos
    c = socket.create_connection(("127.0.0.1", servidor(atender_longitud)))
    enviar_mensaje(c, b"con\nsalto")
    print("C con \\n adentro  :", recibir_mensaje(c))
    enviar_mensaje(c, b"")
    print("C mensaje vacío  :", recibir_mensaje(c))
    paquete = struct.pack("!I", 5) + b"abcde"
    for i in range(0, len(paquete), 2):  # llega en pedazos de 2 bytes
        c.sendall(paquete[i:i + 2])
        time.sleep(0.02)
    print("C en pedazos     :", recibir_mensaje(c))
    c.close()
