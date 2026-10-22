#!/bin/bash

echo "Buscando procesos huérfanos (adoptados por init, PPID=1)..."

# Recorremos todas las carpetas en /proc que sean solo números (los PIDs)
for pid_dir in /proc/[0-9]*; do
    
    # Verificamos que el archivo 'stat' exista y lo podamos leer
    if [ -f "$pid_dir/stat" ] && [ -r "$pid_dir/stat" ]; then
        
        # El archivo 'stat' tiene mucha info. El campo 4 es el PPID (Parent PID)
        ppid=$(awk '{print $4}' "$pid_dir/stat")
        
        # Si el PPID es 1, lo encontramos
        if [ "$ppid" -eq 1 ]; then
            # Extraemos el nombre del proceso (campo 2)
            nombre=$(awk '{print $2}' "$pid_dir/stat")
            # Extraemos el número de PID del nombre de la carpeta
            pid=$(basename "$pid_dir")
            
            echo "Huérfano detectado -> PID: $pid | Proceso: $nombre"
        fi
    fi
done