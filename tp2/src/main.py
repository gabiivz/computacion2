"""Punto de entrada: python -m src.main [--workers 4 --puerto 8000 ...]"""
import logging

import uvicorn

from .app import crear_app
from .config import cargar


class Servidor(uvicorn.Server):
    def handle_exit(self, sig, frame):
        # Handler mínimo, como en el TP1 (clase 6): solo baja una bandera, el trabajo real ocurre afuera.
        # Así POST /tareas empieza a rechazar ya mismo, antes de que uvicorn arranque su cierre y el lifespan espere
        # a las tareas en curso y vuelque el estado.
        self.config.app.state.apagando = True
        super().handle_exit(sig, frame)  # uvicorn: dejar de aceptar conexiones y salir (SIGINT/SIGTERM)


def main(argv=None):
    cfg = cargar(argv)
    logging.basicConfig(level=cfg.log_level.upper(), format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    app = crear_app(cfg)
    Servidor(uvicorn.Config(app, host=cfg.host, port=cfg.puerto, log_level=cfg.log_level.lower())).run()


if __name__ == "__main__":  # imprescindible: con spawn (macOS/Windows) los hijos re-importan este módulo
    main()
