import multiprocessing
from functools import reduce

def mapper(chunk):
    """Cuenta palabras en un bloque de texto."""
    conteo = {}
    for palabra in chunk.lower().split():
        # Limpiar puntuación básica si se desea
        palabra = palabra.strip('.,!?"\'')
        if palabra:
            conteo[palabra] = conteo.get(palabra, 0) + 1
    return conteo

def reducer(dict1, dict2):
    """Combina dos diccionarios."""
    resultado = dict1.copy()
    for palabra, count in dict2.items():
        resultado[palabra] = resultado.get(palabra, 0) + count
    return resultado

def procesar_archivo_map_reduce(ruta_archivo, chunk_size=1024):
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    resultados_parciales = []
    
    # Leer el archivo en fragmentos para no saturar RAM
    with open(ruta_archivo, 'r', encoding='utf-8') as f:
        while True:
            lineas = f.readlines(chunk_size)
            if not lineas:
                break
            texto_chunk = " ".join(lineas)
            # Enviar el chunk de manera asíncrona al Pool
            res = pool.apply_async(mapper, (texto_chunk,))
            resultados_parciales.append(res)
            
    pool.close()
    pool.join()
    
    # Extraer los diccionarios de las promesas asíncronas
    conteos = [res.get() for res in resultados_parciales]
    
    # Reducción final
    if conteos:
        conteo_total = reduce(reducer, conteos)
        return sorted(conteo_total.items(), key=lambda x: -x[1])
    return []