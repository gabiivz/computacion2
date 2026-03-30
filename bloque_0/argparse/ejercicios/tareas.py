"""Gestor de tareas con persistencia y subcomandos."""

import argparse
import sys
import json
from pathlib import Path

DB_PATH = Path.home() / ".tareas.json"

def leer_db():
    if not DB_PATH.exists(): return []
    return json.loads(DB_PATH.read_text())

def guardar_db(tareas):
    DB_PATH.write_text(json.dumps(tareas, indent=4))

def main():
    parser = argparse.ArgumentParser(description="Gestor de Tareas")
    subparsers = parser.add_subparsers(dest="comando", required=True)

    # Subcomando: add
    p_add = subparsers.add_parser("add")
    p_add.add_argument("desc")
    p_add.add_argument("--priority", choices=["baja", "media", "alta"], default="baja")

    # Subcomando: list
    p_list = subparsers.add_parser("list")
    p_list.add_argument("--pending", action="store_true")
    p_list.add_argument("--done", action="store_true")

    # Subcomando: done y remove
    p_done = subparsers.add_parser("done")
    p_done.add_argument("id", type=int)

    p_rem = subparsers.add_parser("remove")
    p_rem.add_argument("id", type=int)

    args = parser.parse_args()
    tareas = leer_db()

    if args.comando == "add":
        t = {"id": len(tareas)+1, "desc": args.desc, "priority": args.priority, "done": False}
        tareas.append(t)
        guardar_db(tareas)
        print(f"Tarea #{t['id']} agregada.")

    elif args.comando == "list":
        for t in tareas:
            if args.pending and t["done"]: continue
            if args.done and not t["done"]: continue
            check = "[x]" if t["done"] else "[ ]"
            prio = f" [{t['priority'].upper()}]" if t['priority'] != "baja" else ""
            print(f"#{t['id']} {check} {t['desc']}{prio}")

    elif args.comando == "done":
        for t in tareas:
            if t["id"] == args.id:
                t["done"] = True
                break
        guardar_db(tareas)
        print(f"Tarea #{args.id} completada.")

    elif args.comando == "remove":
        # Confirmación simple
        confirm = input(f"¿Eliminar tarea #{args.id}? [s/N] ")
        if confirm.lower() == 's':
            tareas = [t for t in tareas if t["id"] != args.id]
            guardar_db(tareas)
            print("Eliminada.")

if __name__ == "__main__":
    main()