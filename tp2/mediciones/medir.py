"""Las 3 mediciones obligatorias del TP2. Uso (desde tp2/, con el venv activo):  python mediciones/medir.py
Levanta su propio servidor de prueba (latencia fija de 0.3 s) y su servidor del TP en puertos libres, y escribe
mediciones/resultados.md con los números para pegar en el README. Los números dependen de TU máquina."""
import asyncio, http.server, os, socketserver, subprocess, sys, tempfile, threading, time
import httpx

LAT = 0.3  # segundos que tarda cada respuesta del servidor local
PORT_LENTO, PORT_API = 9101, 8101
BASE = f"http://127.0.0.1:{PORT_API}"
URL = f"http://127.0.0.1:{PORT_LENTO}/x"
out = []

def log(s=""):
    print(s); out.append(s)

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(LAT); b = b"x" * 1000
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; request_queue_size = 1024

def servidor(*args):
    d = tempfile.mkdtemp()
    p = subprocess.Popen([sys.executable, "-m", "src.main", "--puerto", str(PORT_API), "--datos-dir", d,
                          "--log-level", "WARNING", *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            httpx.get(BASE + "/estadisticas", timeout=0.5); return p
        except httpx.HTTPError: time.sleep(0.1)
    p.kill(); raise SystemExit("el servidor no arrancó")

def parar(p):
    p.terminate()
    try: p.wait(15)
    except subprocess.TimeoutExpired: p.kill()

async def esperar_terminal(c, ids, tope=120):
    """Espera a que no quede nada pendiente ni ejecutando (usa los totales de /estadisticas, no depende del límite del listado)."""
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < tope:
        e = (await c.get(f"{BASE}/estadisticas")).json()["por_estado"]
        if e["pendiente"] == 0 and e["ejecutando"] == 0: return time.perf_counter() - t0
        await asyncio.sleep(0.05)
    return None

async def medicion1():
    log("## Medición 1 — Concurrencia I/O: 20 descargas")
    async with httpx.AsyncClient(timeout=60) as c:
        t0 = time.perf_counter()
        for _ in range(20): await c.get(URL)
        seq = time.perf_counter() - t0
        t0 = time.perf_counter()
        await asyncio.gather(*(c.get(URL) for _ in range(20)))
        con = time.perf_counter() - t0
        r = await c.post(f"{BASE}/tareas", json={"tipo": "descargar", "urls": [URL] * 20})
        t0 = time.perf_counter(); tid = r.json()["id"]; await esperar_terminal(c, [tid]); via_api = time.perf_counter() - t0
    log(f"- 20 secuenciales (cliente): {seq:.2f} s")
    log(f"- 20 concurrentes (cliente, gather): {con:.2f} s  → speedup {seq/con:.1f}x")
    log(f"- 1 tarea `descargar` con 20 URLs vía la API: {via_api:.2f} s  → speedup {seq/via_api:.1f}x (ideal ≈ {LAT:.1f} s)")
    log()

async def latencia_get(c, durante):
    """Mide GET /tareas cada 50 ms mientras corre la tarea pesada."""
    lat = []
    t_fin = time.perf_counter() + durante
    while time.perf_counter() < t_fin:
        t0 = time.perf_counter()
        try: await c.get(f"{BASE}/tareas", params={"limite": 1}, timeout=60)
        except httpx.HTTPError: pass
        lat.append((time.perf_counter() - t0) * 1000)
        await asyncio.sleep(0.05)
    return lat

async def medicion2(iters):
    log(f"## Medición 2 — Event loop bloqueado (hashear {iters:,} iteraciones)")
    res = {}
    for nombre, args in (("SIN executor (hash en el loop)", ["--hash-bloqueante", "true"]), ("CON executor", [])):
        p = servidor(*args)
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                await c.get(f"{BASE}/tareas")
                r = await c.post(f"{BASE}/tareas", json={"tipo": "hashear", "texto": "x", "iteraciones": iters, "timeout": 300})
                tid = r.json()["id"]
                sondeo = asyncio.create_task(latencia_get(c, 4))
                await asyncio.sleep(0.2)
                t = await esperar_terminal(c, [tid], 200)
                lat = await sondeo
            lat.sort()
            res[nombre] = (t, max(lat), lat[len(lat)//2], len(lat))
        finally: parar(p)
    for n, (t, mx, med, k) in res.items():
        log(f"- {n}: tarea completa en {t:.2f} s · GET /tareas durante el hash: máximo {mx:.0f} ms, mediana {med:.1f} ms ({k} sondeos)")
    log()

async def medicion3():
    log("## Medición 3 — Techo del pool (tareas `esperar` de 1 s con 50 workers)")
    p = servidor("--workers", "50", "--cola-max", "20000")
    try:
        async with httpx.AsyncClient(timeout=120, limits=httpx.Limits(max_connections=200)) as c:
            log("| tareas simultáneas | tiempo total | ideal | latencia GET /tareas (máx) | fds | threads | RSS MB |")
            log("|---|---|---|---|---|---|---|")
            for n in (10, 50, 100, 500, 1000, 3000, 10000):
                t0 = time.perf_counter()
                rs = await asyncio.gather(*(c.post(f"{BASE}/tareas", json={"tipo": "esperar", "segundos": 1}) for _ in range(n)))
                ids = [r.json()["id"] for r in rs if r.status_code == 201]
                sondeo = asyncio.create_task(latencia_get(c, 1.5))
                await esperar_terminal(c, ids, 300)
                total = time.perf_counter() - t0
                lat = await sondeo
                e = (await c.get(f"{BASE}/estadisticas")).json().get("proceso", {})
                ideal = -(-len(ids) // 50)
                log(f"| {n} | {total:.1f} s | {ideal} s | {max(lat):.0f} ms | {e.get('fds_abiertos')} | {e.get('threads')} | {e.get('rss_mb')} |")
    finally: parar(p)
    log()

async def main():
    srv = S(("127.0.0.1", PORT_LENTO), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    iters = int(os.environ.get("ITERS", 30_000_000))
    solo = os.environ.get("SOLO", "123")  # p. ej. SOLO=3 repite solo la medición 3
    if "1" in solo:
        p = servidor()
        try: await medicion1()
        finally: parar(p)
    if "2" in solo: await medicion2(iters)
    if "3" in solo: await medicion3()
    os.makedirs("mediciones", exist_ok=True)
    open("mediciones/resultados.md", "w").write("\n".join(out) + "\n")
    print("Escrito en mediciones/resultados.md")

asyncio.run(main())