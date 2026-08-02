import time
import select
import os
import signal
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Group

estado_ui = {
    "vista_activa": 1,
    "criterio_orden": "cpu",
    "saliendo": False
}

intervalos_vistas = {
    1: {"actual": 2.0, "minimo": 0.5},
    2: {"actual": 3.0, "minimo": 1.0},
    3: {"actual": 5.0, "minimo": 2.0},
    4: {"actual": 2.0, "minimo": 0.5},
    5: {"actual": 10.0, "minimo": 5.0},
    6: {"actual": 10.0, "minimo": 5.0},
    7: {"actual": 2.0, "minimo": 1.0}
}

mapa_vistas = {
    '1': 1, 'r': 1,
    '2': 2, 'm': 2,
    '3': 3, 'f': 3,
    '4': 4, 't': 4,
    '5': 5, 's': 5,
    '6': 6, 'p': 6,
    '7': 7, 'g': 7
}

NOMBRE_ANALIZADOR_POR_VISTA = {
    1: "resumen", 2: "memoria", 3: "fds", 4: "threads",
    5: "senales", 6: "scheduling", 7: "sistema"
}

FOOTER_TEXTO = "Vistas: [1-7|r,m,f,t,s,p,g] | Intervalo: [+ / -] | Orden: [c] | Salir: [q]"

valores_intervalos_compartidos = {}


def _propagar_intervalo(vista, nuevo_valor):
    """Empuja el nuevo intervalo al Value compartido del analizador de esa vista."""
    nombre = NOMBRE_ANALIZADOR_POR_VISTA.get(vista)
    valor_compartido = valores_intervalos_compartidos.get(nombre)
    if valor_compartido is not None:
        with valor_compartido.get_lock():
            valor_compartido.value = nuevo_valor

def _filtrar_procesos(items, resumen):
    """Filtra una lista de (pid, datos) según el filtro activo ('/' o 'u')."""
    filtro_texto = estado_ui.get("filtro", "").lower()
    tipo_filtro = estado_ui.get("tipo_filtro", "")
    if not filtro_texto:
        return items

    filtrados = []
    for pid, datos in items:
        r = resumen.get(pid, {})
        if tipo_filtro == "usuario" and filtro_texto not in str(r.get("usuario", "")).lower():
            continue
        if tipo_filtro == "nombre" and filtro_texto not in str(r.get("comando", "")).lower():
            continue
        filtrados.append((pid, datos))
    return filtrados


def _ordenar_procesos(items, resumen, memoria):
    """Ordena una lista de (pid, datos) según el criterio activo (tecla 'c')."""
    def rss_en_kb(pid):
        vmrss = memoria.get(pid, {}).get("vmrss", "0")
        try:
            return int(str(vmrss).split()[0])
        except (ValueError, IndexError):
            return 0

    def cpu_pct(pid):
        return resumen.get(pid, {}).get("cpu_percent", 0.0)

    orden = estado_ui.get("criterio_orden", "cpu")
    if orden == "cpu":
        return sorted(items, key=lambda x: cpu_pct(x[0]), reverse=True)
    elif orden == "rss":
        return sorted(items, key=lambda x: rss_en_kb(x[0]), reverse=True)
    else:
        return sorted(items, key=lambda x: int(x[0]))


def _actualizar_cursor(cantidad_filas):
    """Clampea fila_seleccionada al tamaño de la lista actual y la devuelve."""
    fila_sel = estado_ui.get("fila_seleccionada", 0)
    if cantidad_filas:
        fila_sel = max(0, min(fila_sel, cantidad_filas - 1))
        estado_ui["fila_seleccionada"] = fila_sel
    return fila_sel


def _procesar_pin(pid, indice_fila, fila_sel):
    """Si se apretó Enter estando parado en esta fila, hace toggle del pin.
    El pin guarda el PID, no el índice, así que no se rompe si después si se cambia el orden"""
    if estado_ui.get("accion_pin", False) and indice_fila == fila_sel:
        if estado_ui.get("pin_pid") == pid:
            estado_ui["pin_pid"] = None
        else:
            estado_ui["pin_pid"] = pid
        estado_ui["accion_pin"] = False


def _preparar_lista(items, resumen, memoria):
    """Pipeline compartido: filtra, ordena y clampea el cursor.
    Devuelve (items_listos_para_mostrar, fila_seleccionada)."""
    items = _filtrar_procesos(items, resumen)
    items = _ordenar_procesos(items, resumen, memoria)
    fila_sel = _actualizar_cursor(len(items))
    return items, fila_sel


def procesar_tecla_adicional(tecla):
    """Maneja intervalos, orden, flechas (selección) y enter (pin)."""
    vista_actual = estado_ui.get("vista_activa", 1)

    if tecla in ('+', '=', 'plus'):
        actual = intervalos_vistas[vista_actual]["actual"]
        nuevo = round(actual + 0.5, 1)
        intervalos_vistas[vista_actual]["actual"] = nuevo
        _propagar_intervalo(vista_actual, nuevo)
        return True
    elif tecla in ('-', '_', 'minus'):
        actual = intervalos_vistas[vista_actual]["actual"]
        minimo = intervalos_vistas[vista_actual]["minimo"]
        nuevo = round(max(minimo, actual - 0.5), 1)
        intervalos_vistas[vista_actual]["actual"] = nuevo
        _propagar_intervalo(vista_actual, nuevo)
        return True

    elif tecla == 'c':
        orden = estado_ui.get("criterio_orden", "cpu")
        estado_ui["criterio_orden"] = "rss" if orden == "cpu" else "pid" if orden == "rss" else "cpu"
        estado_ui["fila_seleccionada"] = 0
        return True

    elif tecla in ('\x1b[a', '\x1b[A'):
        actual = estado_ui.get("fila_seleccionada", 0)
        estado_ui["fila_seleccionada"] = max(0, actual - 1)
        return True
    elif tecla in ('\x1b[b', '\x1b[B'):
        actual = estado_ui.get("fila_seleccionada", 0)
        estado_ui["fila_seleccionada"] = actual + 1
        return True

    elif tecla in ('\r', '\n'):
        estado_ui["accion_pin"] = True
        return True

    elif tecla == '/':
        estado_ui["modo_busqueda"] = True
        estado_ui["tipo_filtro"] = "nombre"
        return True
    elif tecla == 'u':
        estado_ui["modo_busqueda"] = True
        estado_ui["tipo_filtro"] = "usuario"
        return True
    elif tecla in ('h', '?'):
        estado_ui["mostrar_ayuda"] = not estado_ui.get("mostrar_ayuda", False)
        return True

    return False


def generar_tabla_resumen(snapshot):
    """Vista 1: Resumen."""
    tabla = Table(expand=True)
    tabla.add_column("PID", style="cyan", justify="right")
    tabla.add_column("PPID", style="cyan", justify="right")
    tabla.add_column("UID/GID + Usuario", style="magenta")
    tabla.add_column("Estado", style="green", justify="center")
    tabla.add_column("Comando", style="white")
    tabla.add_column("CPU %", style="yellow", justify="right")
    tabla.add_column("Threads", style="blue", justify="right")

    try:
        resumen = dict(snapshot.get("resumen", {}))
        memoria = dict(snapshot.get("memoria", {}))
    except Exception:
        resumen = {}
        memoria = {}

    if not resumen:
        tabla.add_row("-", "-", "-", "ESPERANDO DATOS...", "-", "-", "-")
        return tabla

    items, fila_sel = _preparar_lista(list(resumen.items()), resumen, memoria)

    for i, (pid, datos) in enumerate(items[:15]):
        _procesar_pin(pid, i, fila_sel)
        uid_gid_str = f"{datos.get('uid', '?')}/{datos.get('gid', '?')} ({datos.get('usuario', '?')})"
        estilo = "black on white" if i == fila_sel else ""
        cursor = "▶" if i == fila_sel else " "

        tabla.add_row(
            f"{cursor} {pid}",
            str(datos.get("ppid", "?")),
            uid_gid_str,
            str(datos.get("estado", "?")),
            str(datos.get("comando", "?"))[:35],
            f"{datos.get('cpu_percent', 0.0):.1f}%",
            str(datos.get("threads", "?")),
            style=estilo
        )

    return tabla


def generar_tabla_memoria(snapshot):
    """Vista 2: Memoria."""
    tabla = Table(expand=True)
    tabla.add_column("PID", style="cyan", justify="right")
    tabla.add_column("VmSize / VmRSS", style="yellow")
    tabla.add_column("Data / Stk / Exe / Lib", style="magenta")
    tabla.add_column("VmHWM / Swap", style="green")
    tabla.add_column("Faults (Min/Maj)", style="red", justify="center")
    tabla.add_column("Segmentos (text/data/heap/stack/shared)", style="white")

    try:
        memoria = dict(snapshot.get("memoria", {}))
        resumen = dict(snapshot.get("resumen", {}))
    except Exception:
        memoria = {}
        resumen = {}

    if not memoria:
        tabla.add_row("-", "ESPERANDO DATOS...", "-", "-", "-", "-")
        return tabla

    items, fila_sel = _preparar_lista(list(memoria.items()), resumen, memoria)

    for i, (pid, datos) in enumerate(items[:15]):
        _procesar_pin(pid, i, fila_sel)
        vm_sz_rss = f"Virt: {datos.get('vmsize', '?')}\nFis: {datos.get('vmrss', '?')}"
        segmentos_sz = f"D:{datos.get('vmdata', '?')} | S:{datos.get('vmstk', '?')}\nE:{datos.get('vmexe', '?')} | L:{datos.get('vmlib', '?')}"
        hwm_swap = f"HWM: {datos.get('vmhwm', '?')}\nSwap: {datos.get('swap', '?')}"
        faults_str = f"{datos.get('minflt', '?')} / {datos.get('majflt', '?')}"

        segs = datos.get("segmentos", {})
        if isinstance(segs, dict):
            segs_str = f"t:{segs.get('text', 0)} d:{segs.get('data', 0)} h:{segs.get('heap', 0)} s:{segs.get('stack', 0)} sh:{segs.get('shared', 0)}"
        else:
            segs_str = str(segs)

        estilo = "black on white" if i == fila_sel else ""
        cursor = "▶" if i == fila_sel else " "

        tabla.add_row(f"{cursor} {pid}", vm_sz_rss, segmentos_sz, hwm_swap, faults_str, segs_str, style=estilo)

    return tabla


def generar_tabla_fds(snapshot):
    """Vista 3: File Descriptors."""
    tabla = Table(expand=True)
    tabla.add_column("PID", style="cyan", justify="right")
    tabla.add_column("Usuario", style="magenta")
    tabla.add_column("FD", style="yellow", justify="right")
    tabla.add_column("Destino (Target)", style="white")
    tabla.add_column("Tipo", style="green")

    try:
        fds_data = dict(snapshot.get("fds", {}))
        resumen = dict(snapshot.get("resumen", {}))
        memoria = dict(snapshot.get("memoria", {}))
    except Exception:
        fds_data = {}
        resumen = {}
        memoria = {}

    if not fds_data:
        tabla.add_row("-", "-", "-", "ESPERANDO DATOS...", "-")
        return tabla

    limite_items = 15 if estado_ui.get("verbose") else 4
    items, fila_sel = _preparar_lista(list(fds_data.items()), resumen, memoria)

    for i, (pid, lista_fds) in enumerate(items[:15]):
        _procesar_pin(pid, i, fila_sel)
        usuario = resumen.get(pid, {}).get("usuario", "?")
        estilo = "black on white" if i == fila_sel else ""
        cursor = "▶" if i == fila_sel else " "

        if not lista_fds or not isinstance(lista_fds, list):
            tabla.add_row(f"{cursor} {pid}", str(usuario)[:10], "-", "Sin permisos / Sin FDs", "-", style=estilo)
            continue

        for j, fd_info in enumerate(lista_fds[:limite_items]):
            if isinstance(fd_info, dict):
                fd_nro = str(fd_info.get("fd", "?"))
                destino = str(fd_info.get("destino", "?"))
                tipo = str(fd_info.get("tipo", "file"))
            else:
                fd_nro = "?"
                destino = str(fd_info)
                tipo = "file"

            es_primero = (j == 0)
            tabla.add_row(
                f"{cursor} {pid}" if es_primero else "",
                str(usuario)[:10] if es_primero else "",
                fd_nro,
                destino[:45],
                tipo,
                style=estilo
            )

    return tabla


def generar_tabla_threads(snapshot):
    """Vista 4: Threads"""
    tabla = Table(expand=True)
    tabla.add_column("PID", style="cyan", justify="right")
    tabla.add_column("LWP", style="magenta", justify="right")
    tabla.add_column("Usuario", style="magenta")
    tabla.add_column("Estado", style="green", justify="center")
    tabla.add_column("CPU %", style="yellow", justify="right")
    tabla.add_column("Context Sw (Vol/Invol)", style="blue", justify="center")
    tabla.add_column("Nombre del Thread", style="white")

    try:
        threads_data = dict(snapshot.get("threads", {}))
        resumen = dict(snapshot.get("resumen", {}))
        memoria = dict(snapshot.get("memoria", {}))
    except Exception:
        threads_data = {}
        resumen = {}
        memoria = {}

    if not threads_data:
        tabla.add_row("-", "-", "-", "ESPERANDO DATOS...", "-", "-", "-")
        return tabla

    limite_items = 15 if estado_ui.get("verbose") else 4
    items, fila_sel = _preparar_lista(list(threads_data.items()), resumen, memoria)

    for i, (pid, lista_threads) in enumerate(items[:15]):
        _procesar_pin(pid, i, fila_sel)
        usuario = resumen.get(pid, {}).get("usuario", "?")
        estilo = "black on white" if i == fila_sel else ""
        cursor = "▶" if i == fila_sel else " "

        if not lista_threads or not isinstance(lista_threads, list):
            estado_base = resumen.get(pid, {}).get("estado", "?")
            cpu_base = f"{resumen.get(pid, {}).get('cpu_percent', 0.0):.1f}%"
            cmd_base = resumen.get(pid, {}).get("comando", "?")
            tabla.add_row(f"{cursor} {pid}", str(pid), str(usuario)[:10], estado_base, cpu_base, "-", str(cmd_base)[:25], style=estilo)
            continue

        for j, thread_info in enumerate(lista_threads[:limite_items]):
            if isinstance(thread_info, dict):
                lwp = str(thread_info.get("tid", "?"))
                estado = str(thread_info.get("estado", "?"))
                cpu = f"{thread_info.get('cpu_percent', 0.0):.1f}%"
                nombre = str(thread_info.get("nombre", "?"))
                c_vol = thread_info.get("vol_ctxt_switches", "-")
                c_invol = thread_info.get("nonvol_ctxt_switches", "-")
                ctx_sw = f"{c_vol} / {c_invol}"
            else:
                lwp, estado, cpu, nombre, ctx_sw = "?", "0", "0.0%", "?", "- / -"

            es_primero = (j == 0)
            tabla.add_row(
                f"{cursor} {pid}" if es_primero else "",
                lwp,
                str(usuario)[:10] if es_primero else "",
                estado,
                cpu,
                ctx_sw,
                nombre[:25],
                style=estilo
            )

    return tabla


def generar_tabla_senales(snapshot):
    """Vista 5: Señales."""
    tabla = Table(expand=True)
    tabla.add_column("PID", style="cyan", justify="right")
    tabla.add_column("Usuario", style="magenta")
    tabla.add_column("SigBlk", style="red")
    tabla.add_column("SigIgn", style="dim")
    tabla.add_column("SigCgt", style="green")
    tabla.add_column("SigPnd", style="yellow")
    tabla.add_column("ShdPnd", style="yellow")
    tabla.add_column("Comando", style="white")

    try:
        senales_data = dict(snapshot.get("senales", {}))
        resumen = dict(snapshot.get("resumen", {}))
        memoria = dict(snapshot.get("memoria", {}))
    except Exception:
        senales_data = {}
        resumen = {}
        memoria = {}

    if not senales_data:
        tabla.add_row("-", "-", "ESPERANDO DATOS...", "-", "-", "-", "-", "-")
        return tabla

    items, fila_sel = _preparar_lista(list(senales_data.items()), resumen, memoria)

    for i, (pid, datos) in enumerate(items[:15]):
        _procesar_pin(pid, i, fila_sel)
        usuario = resumen.get(pid, {}).get("usuario", "?")
        comando = resumen.get(pid, {}).get("comando", "?")

        if isinstance(datos, dict):
            sigblk = str(datos.get("SigBlk", "-"))
            sigign = str(datos.get("SigIgn", "-"))
            sigcgt = str(datos.get("SigCgt", "-"))
            sigpnd = str(datos.get("SigPnd", "-"))
            shdpnd = str(datos.get("ShdPnd", "-"))
        else:
            sigblk, sigign, sigcgt, sigpnd, shdpnd = "-", "-", "-", "-", "-"

        estilo = "black on white" if i == fila_sel else ""
        cursor = "▶" if i == fila_sel else " "

        tabla.add_row(
            f"{cursor} {pid}", str(usuario)[:10],
            sigblk[:12], sigign[:12], sigcgt[:12], sigpnd[:12], shdpnd[:12],
            str(comando)[:25],
            style=estilo
        )

    return tabla


def generar_tabla_scheduling(snapshot):
    """Vista 6: Scheduling."""
    tabla = Table(expand=True)
    tabla.add_column("PID", style="cyan", justify="right")
    tabla.add_column("Usuario", style="magenta")
    tabla.add_column("Policy / RT", style="yellow")
    tabla.add_column("Prio / Nice", style="green", justify="center")
    tabla.add_column("Ctx Sw (Vol/Invol)", style="red", justify="center")
    tabla.add_column("Utime / Stime", style="blue", justify="center")
    tabla.add_column("Affinity", style="dim")
    tabla.add_column("SID / PGID", style="dim", justify="center")
    tabla.add_column("Comando", style="white")

    try:
        sched_data = dict(snapshot.get("scheduling", {}))
        resumen = dict(snapshot.get("resumen", {}))
        memoria = dict(snapshot.get("memoria", {}))
    except Exception:
        sched_data = {}
        resumen = {}
        memoria = {}

    if not sched_data:
        tabla.add_row("-", "-", "ESPERANDO DATOS...", "-", "-", "-", "-", "-", "-")
        return tabla

    items, fila_sel = _preparar_lista(list(sched_data.items()), resumen, memoria)

    for i, (pid, datos) in enumerate(items[:15]):
        _procesar_pin(pid, i, fila_sel)
        usuario = resumen.get(pid, {}).get("usuario", "?")
        comando = resumen.get(pid, {}).get("comando", "?")

        if isinstance(datos, dict):
            policy_rt = f"{datos.get('policy', '?')} (RT:{datos.get('rt_priority', 0)})"
            prio_nice = f"{datos.get('priority', '?')} / {datos.get('nice', '?')}"
            ctx_sw = f"{datos.get('vol_ctxt_switches', '-')} / {datos.get('nonvol_ctxt_switches', '-')}"
            ut_st = f"{datos.get('utime', '?')} / {datos.get('stime', '?')}"
            affinity = str(datos.get("cpu_affinity", "?"))
            sid_pgid = f"{datos.get('sid', '?')} / {datos.get('pgid', '?')}"
        else:
            policy_rt, prio_nice, ctx_sw, ut_st, affinity, sid_pgid = "?", "?", "?", "?", "?", "?"

        estilo = "black on white" if i == fila_sel else ""
        cursor = "▶" if i == fila_sel else " "

        tabla.add_row(
            f"{cursor} {pid}", str(usuario)[:10],
            policy_rt, prio_nice, ctx_sw, ut_st,
            affinity[:10], sid_pgid, str(comando)[:20],
            style=estilo
        )

    return tabla


def generar_tabla_globales(snapshot):
    """Vista 7: Dashboard global del sistema"""
    tabla = Table(title="[ Dashboard Global del Sistema ]", expand=True, border_style="cyan")
    tabla.add_column("Métrica del Sistema", style="magenta", justify="right", width=32)
    tabla.add_column("Valor Actual", style="blue")

    try:
        globales = dict(snapshot.get("globales", {}))
    except Exception:
        globales = {}

    if not globales:
        tabla.add_row("Estado del Recolector", "ESPERANDO DATOS GLOBALES...")
        return tabla

    cpu_global = globales.get("cpu_global", globales.get("cpu", "U:? S:? I:? IO:?"))
    load_avg = globales.get("load_avg", globales.get("loadavg", "?"))

    mem = globales.get("memoria", globales.get("meminfo", {}))
    if isinstance(mem, dict):
        mem_str = f"Tot: {mem.get('total','?')}, Lib: {mem.get('free','?')}, Buf: {mem.get('buffers','?')}, Cach: {mem.get('cached','?')}, Swap: {mem.get('swap','?')}"
    else:
        mem_str = str(mem)

    proc = globales.get("procesos_stats", globales.get("procesos", {}))
    if isinstance(proc, dict):
        proc_str = f"Tot: {proc.get('total','?')}, Run: {proc.get('running','?')}, Sleep: {proc.get('sleeping','?')}, Zomb: {proc.get('zombies','?')}, Thr: {proc.get('threads','?')}"
    else:
        proc_str = str(proc)

    uptime = globales.get("uptime", globales.get("up_boot", "Uptime: ? / Boot: ?"))

    top_cpu_data = globales.get("top_cpu", globales.get("top3_cpu", ["?"]))
    top_ram_data = globales.get("top_ram", globales.get("top3_ram", ["?"]))
    top_cpu = " | ".join(map(str, top_cpu_data)) if isinstance(top_cpu_data, list) else str(top_cpu_data)
    top_ram = " | ".join(map(str, top_ram_data)) if isinstance(top_ram_data, list) else str(top_ram_data)

    tabla.add_row("CPU Global (usr/sys/idle/iowait)", str(cpu_global))
    tabla.add_row("Load Average (1m, 5m, 15m)", str(load_avg))
    tabla.add_row("Memoria (total/libre/buffers/cached/swap)", mem_str)
    tabla.add_row("Procesos (totales/estados/threads/zombies)", proc_str)
    tabla.add_row("Uptime / Boot Time", str(uptime))
    tabla.add_row("Top 3 Procesos (por CPU)", top_cpu)
    tabla.add_row("Top 3 Procesos (por Memoria)", top_ram)

    return tabla


def generar_panel_detalle(snapshot):
    """Panel de detalle del proceso pineado (Enter)"""
    pin_pid = estado_ui.get("pin_pid")
    if pin_pid is None:
        return None

    r = snapshot.get("resumen", {}).get(pin_pid)
    m = snapshot.get("memoria", {}).get(pin_pid)
    s = snapshot.get("scheduling", {}).get(pin_pid)

    if r is None:
        return Panel(f"[red]PID {pin_pid} - Proceso no disponible (murió)[/red]", border_style="red")

    texto = f"[bold cyan]DETALLE - PID {pin_pid}: {r.get('comando', '?')}[/bold cyan]\n"
    texto += f"Estado: {r.get('estado', '?')} | CPU: {r.get('cpu_percent', 0):.1f}% | Threads: {r.get('threads', '?')} | PPID: {r.get('ppid', '?')}\n"

    if m:
        texto += f"VmRSS: {m.get('vmrss', '?')} | VmSize: {m.get('vmsize', '?')} | MinFlt: {m.get('minflt', '?')} | MajFlt: {m.get('majflt', '?')}\n"
    if s:
        vol = s.get('vol_ctxt_switches', '?')
        invol = s.get('nonvol_ctxt_switches', '?')
        texto += f"Nice: {s.get('nice', '?')} | Prio: {s.get('priority', '?')} | Policy: {s.get('policy', '?')} | Ctxt (vol/nonvol): {vol}/{invol}"

    return Panel(texto, border_style="magenta", title="[ Pin ]")


def generar_panel_ayuda():
    """Tabla de keybindings obligatorios."""
    tabla = Table(title="[ Ayuda y Teclas Obligatorias ]", expand=True)
    tabla.add_column("Tecla", style="cyan", justify="center")
    tabla.add_column("Acción", style="white")

    tabla.add_row("1-7 o r/m/f/t/s/p/g", "Cambiar de vista")
    tabla.add_row("↑ / ↓", "Navegar por la lista de procesos (vistas 1-6)")
    tabla.add_row("Enter", "Pin del proceso seleccionado (vistas 1-6)")
    tabla.add_row("/", "Filtrar por nombre de comando")
    tabla.add_row("u", "Filtrar por usuario")
    tabla.add_row("c", "Toggle ordenamiento (CPU% / RSS / PID)")
    tabla.add_row("+ / -", "Ajustar intervalo de la vista activa")
    tabla.add_row("q", "Salir limpiamente")
    tabla.add_row("h / ?", "Mostrar / Ocultar esta ayuda")

    return Panel(tabla, border_style="yellow")


def generar_panel_central(snapshot):
    """Enrutador principal: búsqueda, tabla activa y panel de detalle."""
    if estado_ui.get("mostrar_ayuda", False):
        return generar_panel_ayuda()

    vista = estado_ui.get("vista_activa", 1)

    if vista == 1:
        tabla_principal = Panel(generar_tabla_resumen(snapshot), title="[ Vista 1: Resumen ]", border_style="green")
    elif vista == 2:
        tabla_principal = Panel(generar_tabla_memoria(snapshot), title="[ Vista 2: Memoria ]", border_style="blue")
    elif vista == 3:
        tabla_principal = Panel(generar_tabla_fds(snapshot), title="[ Vista 3: FDs ]", border_style="yellow")
    elif vista == 4:
        tabla_principal = Panel(generar_tabla_threads(snapshot), title="[ Vista 4: Threads ]", border_style="magenta")
    elif vista == 5:
        tabla_principal = Panel(generar_tabla_senales(snapshot), title="[ Vista 5: Señales ]", border_style="green")
    elif vista == 6:
        tabla_principal = Panel(generar_tabla_scheduling(snapshot), title="[ Vista 6: Scheduling ]", border_style="cyan")
    elif vista == 7:
        tabla_principal = generar_tabla_globales(snapshot)
    else:
        tabla_principal = Panel(f"Vista {vista} no implementada.", border_style="red")

    panel_pin = generar_panel_detalle(snapshot)

    elementos_pantalla = []

    if estado_ui.get("modo_busqueda"):
        tipo = estado_ui.get("tipo_filtro", "")
        texto = estado_ui.get("filtro", "")
        elementos_pantalla.append(Panel(f"Buscando por {tipo}: [bold yellow]{texto}_[/bold yellow]", border_style="red"))

    elementos_pantalla.append(tabla_principal)

    if panel_pin and vista != 7:
        elementos_pantalla.append(panel_pin)

    return Group(*elementos_pantalla)


def display_worker(snapshot, verbose_flag=None, intervalos_compartidos=None, seguir_corriendo=None):
    global valores_intervalos_compartidos
    if intervalos_compartidos:
        valores_intervalos_compartidos = intervalos_compartidos

    time.sleep(1)

    import termios
    import tty

    try:
        fd = os.open('/dev/tty', os.O_RDONLY | os.O_NONBLOCK)
        configuracion_original = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        atributos = termios.tcgetattr(fd)
        atributos[3] = atributos[3] & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, atributos)
    except Exception:
        fd = None

    pantalla = Layout()
    pantalla.split_column(
        Layout(Panel("[bold cyan]Monitor de Sistema - TP1[/bold cyan]"), size=3),
        Layout(name="cuerpo"),
        Layout(name="footer", size=3)
    )
    pantalla["footer"].update(Panel(FOOTER_TEXTO, border_style="dim"))

    ultima_revision_filtro = -1

    try:
        with Live(pantalla, refresh_per_second=4, screen=True) as live:
            while not estado_ui.get("saliendo", False) and (seguir_corriendo is None or seguir_corriendo.value):

                if verbose_flag is not None:
                    estado_ui["verbose"] = bool(verbose_flag.value)

                revision_actual = snapshot.get("config_revision", 0)
                if revision_actual != ultima_revision_filtro:
                    filtro_cfg = snapshot.get("config_filtro", {})
                    if isinstance(filtro_cfg, dict):
                        estado_ui["tipo_filtro"] = filtro_cfg.get("tipo", "")
                        estado_ui["filtro"] = filtro_cfg.get("texto", "")
                        estado_ui["fila_seleccionada"] = 0
                    ultima_revision_filtro = revision_actual

                if fd is not None and select.select([fd], [], [], 0.05)[0]:
                    try:
                        primer_byte = os.read(fd, 1)
                        if primer_byte:
                            if primer_byte == b'\x1b':
                                resto = b''
                                if select.select([fd], [], [], 0.02)[0]:
                                    resto = os.read(fd, 2)
                                byte_leido = primer_byte + resto
                            else:
                                byte_leido = primer_byte

                            tecla = byte_leido.decode('utf-8', errors='ignore').lower()

                            if estado_ui.get("modo_busqueda"):
                                if tecla in ('\r', '\n'):
                                    estado_ui["modo_busqueda"] = False
                                elif byte_leido in (b'\x7f', b'\x08'):
                                    estado_ui["filtro"] = estado_ui.get("filtro", "")[:-1]
                                elif tecla == '\x1b':
                                    estado_ui["modo_busqueda"] = False
                                    estado_ui["filtro"] = ""
                                elif tecla.isprintable():
                                    estado_ui["filtro"] = estado_ui.get("filtro", "") + tecla
                                    estado_ui["fila_seleccionada"] = 0
                                continue

                            if not tecla.strip() and tecla not in (' ', '\r', '\n') and not byte_leido.startswith(b'\x1b['):
                                pass
                            elif tecla == 'q':
                                estado_ui["saliendo"] = True
                                break
                            elif tecla in mapa_vistas:
                                estado_ui["vista_activa"] = mapa_vistas[tecla]
                                estado_ui["mostrar_ayuda"] = False
                            else:
                                try:
                                    procesar_tecla_adicional(tecla)
                                except Exception:
                                    pass
                    except BlockingIOError:
                        pass

                try:
                    pantalla["cuerpo"].update(generar_panel_central(snapshot))
                except Exception as e:
                    pantalla["cuerpo"].update(Panel(f"Error interno dibujando: {e}", border_style="red"))

                time.sleep(0.05)

    except KeyboardInterrupt:
        pass
    finally:
        if fd is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, configuracion_original)
            os.close(fd)
        os.kill(os.getppid(), signal.SIGINT)