"""Clase 16 - Ej 2 (obligatorio): mixins de socketserver, orden de herencia y estado con fork."""
import multiprocessing
import socket
import socketserver
import threading
import time


class Bien(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class Mal(socketserver.TCPServer, socketserver.ThreadingMixIn):
    pass


class LentoHandler(socketserver.BaseRequestHandler):
    def handle(self):
        time.sleep(0.5)
        self.request.sendall(b"ok")


def parte_b():
    for C in (Bien, Mal):
        mro = [k.__name__ for k in C.__mro__][:4]
        quien = next(k.__name__ for k in C.__mro__ if "process_request" in k.__dict__)
        print(f"{C.__name__:5s} MRO={mro} process_request viene de: {quien}")

    for C in (Bien, Mal):
        srv = C(("127.0.0.1", 0), LentoHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        t0 = time.time()

        def cliente():
            with socket.create_connection(srv.server_address) as s:
                s.recv(10)

        hs = [threading.Thread(target=cliente) for _ in range(2)]
        for h in hs:
            h.start()
        for h in hs:
            h.join()
        print(f"{C.__name__:5s} 2 clientes lentos tardaron {time.time() - t0:.2f}s "
              f"({'paralelo' if time.time() - t0 < 0.8 else 'SECUENCIAL, sin error ni aviso'})")
        srv.shutdown()
        srv.server_close()


# ---- Parte C: contador compartido con fork ----
class ContadorHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.server.contador.value += 1  # en un proceso hijo, sin Value sería una copia
        self.request.sendall(str(self.server.contador.value).encode())


class ForkSinValue(socketserver.ForkingMixIn, socketserver.TCPServer):
    contador_local = 0


class ForkConValue(socketserver.ForkingMixIn, socketserver.TCPServer):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.contador = multiprocessing.Value("i", 0)  # en __init__ del servidor: ANTES del fork


class HandlerLocal(socketserver.BaseRequestHandler):
    def handle(self):
        self.server.contador_local += 1  # modifica la copia del hijo
        self.request.sendall(str(self.server.contador_local).encode())


def pedir(addr):
    with socket.create_connection(addr) as s:
        return s.recv(10).decode()


def parte_c():
    for clase, handler, nombre in ((ForkSinValue, HandlerLocal, "fork sin Value"),
                                   (ForkConValue, ContadorHandler, "fork con Value")):
        srv = clase(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f"{nombre}: 5 clientes ven el contador -> {[pedir(srv.server_address) for _ in range(5)]}")
        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    parte_b()
    parte_c()
