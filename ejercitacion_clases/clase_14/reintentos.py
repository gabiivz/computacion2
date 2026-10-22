def pedir_con_reintentos(sock, mensaje, destino, intentos=3, timeout=3.0):
    """Manda un mensaje y espera respuesta, reintentando si se pierde."""
    sock.settimeout(timeout)
    for intento in range(1, intentos + 1):
        sock.sendto(mensaje, destino)
        try:
            respuesta, _ = sock.recvfrom(65535)
            return respuesta
        except TimeoutError:
            print(f'Intento {intento}: sin respuesta, reintento')
    return None