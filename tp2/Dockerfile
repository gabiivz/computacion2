FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

EXPOSE 8000

# `python -m` (y no uvicorn por CLI) para pasar por nuestro main: argparse + handler de señales + guarda __main__.
# Como PID 1 recibe SIGTERM de `docker stop`; uvicorn la captura y dispara el apagado ordenado.
CMD ["python", "-m", "src.main"]
