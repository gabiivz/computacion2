"""Clase 15 - Ej 3 (obligatorio): confiabilidad sobre UDP. Reintentos, duplicados y números de secuencia."""
import random
import socket
import struct
import sys
import threading

PERDIDA = 0.3  # probabilidad de perder cada datagrama (se aplica en ambos sentidos)


def empaquetar(seq, payload):
    return struct.pack("!I", seq) + payload


def desempaquetar(datos):
    (seq,) = struct.unpack("!I", datos[:4])
    return seq, datos[4:]


class Servidor(threading.Thread):
    """Eco en mayúsculas. Cuenta cuántas veces hizo el 'trabajo real'."""

    def __init__(self, con_seq):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.addr = self.sock.getsockname()
        self.con_seq = con_seq
        self.trabajos = 0
        self.vistos = {}  # seq -> respuesta ya calculada (para reenviar sin repetir el trabajo)

    def enviar(self, datos, destino):
        if random.random() >= PERDIDA:  # perdemos la respuesta con la misma probabilidad
            self.sock.sendto(datos, destino)

    def run(self):
        while True:
            datos, origen = self.sock.recvfrom(4096)
            if self.con_seq:
                seq, payload = desempaquetar(datos)
                if seq in self.vistos:  # duplicado: reenviar lo guardado, NO volver a trabajar
                    self.enviar(self.vistos[seq], origen)
                    continue
                self.trabajos += 1
                resp = empaquetar(seq, payload.upper())
                self.vistos[seq] = resp
                self.enviar(resp, origen)
            else:
                self.trabajos += 1
                self.enviar(datos.upper(), origen)


def pedir_con_reintentos(sock, mensaje, destino, seq=None, intentos=80, timeout=0.02):
    """Devuelve (respuesta, intentos_usados). Descarta respuestas con seq distinto al pedido en curso."""
    paquete = empaquetar(seq, mensaje) if seq is not None else mensaje
    for n in range(1, intentos + 1):
        if random.random() >= PERDIDA:  # perdida del pedido
            sock.sendto(paquete, destino)
        sock.settimeout(timeout)
        try:
            while True:
                datos, _ = sock.recvfrom(4096)
                if seq is None:
                    return datos, n
                rseq, payload = desempaquetar(datos)
                if rseq == seq:
                    return payload, n
                # respuesta tardía de un pedido anterior: se ignora y se sigue esperando
        except socket.timeout:
            continue
    raise TimeoutError("sin respuesta")


def experimento(con_seq, pedidos=100):
    srv = Servidor(con_seq)
    srv.start()
    cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    total_intentos = 0
    for i in range(pedidos):
        _, n = pedir_con_reintentos(cli, b"hola", srv.addr, seq=i if con_seq else None)
        total_intentos += n
    print(f"{'con seq' if con_seq else 'sin seq'}: pedidos={pedidos} envíos reales={total_intentos} "
          f"veces que el servidor trabajó={srv.trabajos} "
          f"-> {'trabajo duplicado' if srv.trabajos > pedidos else 'exactamente una vez'}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        PERDIDA = float(sys.argv[1])
    print(f"pérdida simulada = {PERDIDA}")
    experimento(con_seq=False)
    experimento(con_seq=True)
