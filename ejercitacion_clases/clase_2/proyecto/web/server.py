from flask import Flask, jsonify
import redis

app = Flask(__name__)
r = redis.Redis(host='redis', port=6379, decode_responses=True)

@app.route('/', methods=['GET'])
def index():
    try:
        # Obtenemos el valor, o 0 si todavía no existe
        valor_actual = r.get('contador') or 0
        return jsonify({
            "mensaje": "¡Sistema funcionando perfecto!",
            "contador": valor_actual
        })
    except redis.ConnectionError:
        return jsonify({"error": "Base de datos desconectada"}), 500

if __name__ == '__main__':
    # Es vital escuchar en 0.0.0.0 para que Docker pueda exponer el puerto hacia Windows
    app.run(host='0.0.0.0', port=5000)