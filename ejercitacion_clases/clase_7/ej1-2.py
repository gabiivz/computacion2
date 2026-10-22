import mmap
import os

nombre_archivo = "archivo_tarea.txt"

# 1. Crear el archivo con 5 líneas de texto (preparación del entorno)
with open(nombre_archivo, "w") as f:
    f.write("Línea 1: Este es el inicio.\n")
    f.write("Línea 2: Todo marcha bien.\n")
    f.write("Línea 3: Tenemos un GATO en la casa.\n")
    f.write("Línea 4: Ya casi terminamos.\n")
    f.write("Línea 5: Fin del texto.\n")

print("Archivo original creado.")

# 2. Abrir el archivo en modo lectura/escritura binaria ("r+b")
with open(nombre_archivo, "r+b") as f:
    
    # Mapeamos con permisos de escritura (ACCESS_WRITE)
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE)
    
    # 3. Definir la palabra a buscar y el reemplazo 
    # OJO: mmap trabaja con bytes, por eso la 'b' antes de las comillas.
    # Tienen que tener EXACTAMENTE la misma cantidad de letras.
    palabra_buscar = b"GATO"
    palabra_nueva = b"PATO" 
    
    # Buscar la palabra
    indice = mm.find(palabra_buscar)
    
    if indice != -1:
        print(f"Palabra '{palabra_buscar.decode()}' encontrada en la posición {indice}.")
        
        # 4. Reemplazar la palabra usando slices (rebanadas)
        # Vamos desde el índice encontrado, hasta el índice + el largo de la palabra
        mm[indice : indice + len(palabra_buscar)] = palabra_nueva
        
        print(f"Reemplazada exitosamente por '{palabra_nueva.decode()}'.")
    else:
        print("No se encontró la palabra.")
        
    # Siempre hay que cerrar el mapa al terminar
    mm.close()