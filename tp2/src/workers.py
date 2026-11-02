"""Pool de workers: N corrutinas que consumen de la cola compartida (productor-consumidor, clase 11, pero con corrutinas).

Cada tarea corre en su PROPIA asyncio.Task (`inner`), distinta de la del worker. Así se puede cancelar una tarea en
ejecución (DELETE) sin matar al worker que la estaba esperando.
"""
import asyncio
import logging
import time

from .cola import ColaTareas
from .estado import Registro, Tarea
from .modelos import TERMINALES, Estado
from .tareas import EJECUTORES, Contexto

log = logging.getLogger("tareas.workers")


class Pool:
    def __init__(self, cola: ColaTareas, registro: Registro, ctx: Contexto, n: int):
        self.cola, self.registro, self.ctx, self.n = cola, registro, ctx, n
        self.workers: list[asyncio.Task] = []
        self.ocupados: set[int] = set()
        self.cerrando = False

    # ---------------- ciclo de vida ----------------
    def iniciar(self):
        self.workers = [self._lanzar(i) for i in range(self.n)]

    def _lanzar(self, i: int) -> asyncio.Task:
        t = asyncio.create_task(self._worker(i), name=f"worker-{i}")
        t.add_done_callback(lambda fin, i=i: self._murio(i, fin))
        return t

    def _murio(self, i: int, t: asyncio.Task):
        """Red de seguridad: si un worker termina por una excepción inesperada, se loguea y se lo reemplaza."""
        if self.cerrando or t.cancelled():
            return
        log.error("worker-%d murió inesperadamente (%r); se lo reemplaza", i, t.exception())
        self.ocupados.discard(i)
        self.workers[i] = self._lanzar(i)

    async def detener(self, limite: float):
        """Apagado ordenado: no toman tareas nuevas; se espera `limite` s a las que están en curso; el resto se corta."""
        self.cerrando = True
        for i, w in enumerate(self.workers):
            if i not in self.ocupados:
                w.cancel()  # ocioso: está bloqueado en get(), no tiene nada a medias; cancelar es seguro
        activos = [w for w in self.workers if not w.done()]
        if activos:
            _, pendientes = await asyncio.wait(activos, timeout=limite)
            for w in pendientes:
                log.warning("%s no terminó en %.1fs: se cancela su tarea", w.get_name(), limite)
                w.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)

    # ---------------- el worker ----------------
    async def _worker(self, i: int):
        while not self.cerrando:
            tid = await self.cola.obtener()
            self.ocupados.add(i)  # sin await entre obtener() y esto: el estado es consistente
            try:
                tarea = self.registro.get(tid)
                if tarea is not None and tarea.estado is Estado.PENDIENTE:  # si la cancelaron en la cola, se saltea
                    await self._ejecutar(tarea)
            except Exception:
                # Un bug propio no puede matar al worker: se loguea y sigue con la próxima.
                log.exception("error inesperado en worker-%d con la tarea %s", i, tid)
            finally:  # va en finally: si no, join() de la cola nunca termina cuando una tarea falla (clase 21)
                self.ocupados.discard(i)
                self.cola.hecha()

    async def _ejecutar(self, tarea: Tarea):
        tarea.estado, tarea.iniciada = Estado.EJECUTANDO, time.time()
        inner = asyncio.create_task(EJECUTORES[tarea.tipo](tarea.params, self.ctx), name=f"tarea-{tarea.id}")
        tarea.handle = inner
        try:
            tarea.resultado = await asyncio.wait_for(inner, tarea.timeout)  # al vencer, wait_for cancela a inner
            tarea.terminar(Estado.COMPLETADA)
        except TimeoutError:
            tarea.terminar(Estado.FALLIDA, f"timeout: superó {tarea.timeout}s")
        except asyncio.CancelledError:
            # Dos orígenes posibles: (a) cancelaron la TAREA (DELETE): el worker sigue vivo;
            # (b) cancelaron al WORKER (apagado): hay que propagar. cancelling() > 0 distingue (b).
            if asyncio.current_task().cancelling():
                tarea.terminar(Estado.CANCELADA, "interrumpida por apagado")
                raise
            tarea.terminar(Estado.CANCELADA, "cancelada por el cliente")
        except Exception as e:
            tarea.terminar(Estado.FALLIDA, f"{type(e).__name__}: {e}")
        finally:
            if tarea.estado not in TERMINALES:  # red de seguridad: nunca dejar una tarea en 'ejecutando'
                tarea.terminar(Estado.FALLIDA, "terminó sin estado final")

    # ---------------- cancelación pedida por la API ----------------
    async def cancelar(self, tarea: Tarea, espera: float = 5.0):
        if tarea.estado is Estado.PENDIENTE:
            tarea.terminar(Estado.CANCELADA, "cancelada antes de ejecutarse")  # el worker la saltea al sacarla de la cola
        elif tarea.estado is Estado.EJECUTANDO and tarea.handle is not None:
            tarea.handle.cancel()
            try:
                await asyncio.wait_for(tarea.fin.wait(), espera)  # que la respuesta refleje el estado final
            except TimeoutError:
                log.warning("tarea %d tarda en cancelarse (¿trozo de CPU en curso?)", tarea.id)
