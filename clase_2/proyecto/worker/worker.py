import time
import redis

# Docker Compose hace magia: el 'host' es directamente el nombre del servicio
r = redis.Redis(host='redis', port=6379, decode_responses=True)

print("Iniciando el Worker...")
while True:
    try:
        r.incr('contador')
        print(f"Contador actualizado a: {r.get('contador')}")
    except redis.ConnectionError:
        print("Esperando a que Redis levante...")
    
    time.sleep(1)