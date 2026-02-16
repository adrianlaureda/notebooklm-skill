#!/usr/bin/env python3
"""
Gestión de notebooks: create, list, delete, get + sincronización con library.json.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from nlm_client import _create_client, run_async

SKILL_DIR = Path(__file__).parent.parent
LIBRARY_FILE = SKILL_DIR / "data" / "library.json"


def _load_library() -> dict:
    """Carga library.json o crea estructura vacía."""
    if LIBRARY_FILE.exists():
        return json.loads(LIBRARY_FILE.read_text())
    return {"notebooks": {}, "active_notebook_id": None, "last_sync": None}


def _save_library(data: dict):
    """Guarda library.json."""
    data["last_sync"] = datetime.now().isoformat()
    LIBRARY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _nb_to_entry(nb) -> dict:
    """Convierte un Notebook de la API a entrada de library.json."""
    return {
        "id": nb.id,
        "name": nb.title,
        "url": f"https://notebooklm.google.com/notebook/{nb.id}",
        "description": f"Cuaderno: {nb.title}",
        "topics": ["general"],
        "use_cases": ["consulta"],
        "tags": [],
        "sources_count": getattr(nb, "sources_count", 0),
        "use_count": 0,
        "added_at": datetime.now().strftime("%Y-%m-%d"),
        "last_used": None,
    }


def cmd_list():
    """Lista todos los notebooks desde la API y sincroniza library.json."""

    async def _list():
        async with await _create_client() as client:
            notebooks = await client.notebooks.list()
            library = _load_library()

            for nb in notebooks:
                if nb.id not in library["notebooks"]:
                    library["notebooks"][nb.id] = _nb_to_entry(nb)
                else:
                    # Actualizar nombre por si cambió
                    library["notebooks"][nb.id]["name"] = nb.title

            _save_library(library)

            print(f"NOTEBOOKS: {len(notebooks)}")
            for nb in notebooks:
                marker = " *" if nb.id == library.get("active_notebook_id") else ""
                print(f"  [{nb.id[:8]}...] {nb.title}{marker}")
            return 0

    return run_async(_list())


def cmd_create(name: str):
    """Crea un nuevo notebook."""

    async def _create():
        async with await _create_client() as client:
            nb = await client.notebooks.create(name)
            library = _load_library()
            library["notebooks"][nb.id] = _nb_to_entry(nb)
            library["active_notebook_id"] = nb.id
            _save_library(library)

            print(f"CREADO: {nb.title}")
            print(f"  ID: {nb.id}")
            print(f"  URL: https://notebooklm.google.com/notebook/{nb.id}")
            print(f"  (activado automáticamente)")
            return 0

    return run_async(_create())


def cmd_delete(notebook_id: str):
    """Elimina un notebook."""

    async def _delete():
        async with await _create_client() as client:
            # Resolver ID parcial
            full_id = _resolve_id(notebook_id)
            result = await client.notebooks.delete(full_id)
            if result:
                library = _load_library()
                library["notebooks"].pop(full_id, None)
                if library.get("active_notebook_id") == full_id:
                    library["active_notebook_id"] = None
                _save_library(library)
                print(f"ELIMINADO: {full_id}")
            else:
                print(f"ERROR al eliminar: {full_id}")
            return 0 if result else 1

    return run_async(_delete())


def cmd_get(notebook_id: str):
    """Muestra detalles de un notebook."""

    async def _get():
        full_id = _resolve_id(notebook_id)
        async with await _create_client() as client:
            nb = await client.notebooks.get(full_id)
            print(f"NOTEBOOK: {nb.title}")
            print(f"  ID: {nb.id}")
            print(f"  Fuentes: {getattr(nb, 'sources_count', '?')}")

            # Intentar obtener descripción
            try:
                desc = await client.notebooks.get_description(nb.id)
                if desc.summary:
                    print(f"  Resumen: {desc.summary[:200]}")
            except Exception:
                pass

            # Listar fuentes
            try:
                sources = await client.sources.list(nb.id)
                if sources:
                    print(f"\n  FUENTES ({len(sources)}):")
                    for src in sources:
                        title = getattr(src, "title", None) or "(sin título)"
                        print(f"    - {title}")
            except Exception:
                pass

            return 0

    return run_async(_get())


def cmd_activate(notebook_id: str):
    """Establece el notebook activo."""
    full_id = _resolve_id(notebook_id)
    library = _load_library()
    if full_id not in library["notebooks"]:
        print(f"ERROR: Notebook {full_id} no está en library.json")
        print("  Ejecuta primero: python scripts/run.py nlm_notebook.py list")
        return 1
    library["active_notebook_id"] = full_id
    _save_library(library)
    name = library["notebooks"][full_id].get("name", full_id)
    print(f"ACTIVADO: {name} [{full_id[:8]}...]")
    return 0


def cmd_sync():
    """Sincroniza library.json con notebooks reales de la API."""

    async def _sync():
        async with await _create_client() as client:
            notebooks = await client.notebooks.list()
            api_ids = {nb.id for nb in notebooks}
            library = _load_library()

            # Añadir nuevos
            added = 0
            for nb in notebooks:
                if nb.id not in library["notebooks"]:
                    library["notebooks"][nb.id] = _nb_to_entry(nb)
                    added += 1

            # Marcar eliminados
            removed = 0
            for nid in list(library["notebooks"].keys()):
                if nid not in api_ids:
                    library["notebooks"].pop(nid)
                    removed += 1

            _save_library(library)
            print(f"SYNC: {len(notebooks)} notebooks ({added} nuevos, {removed} eliminados)")
            return 0

    return run_async(_sync())


def _resolve_id(partial_id: str) -> str:
    """Resuelve un ID parcial a ID completo usando library.json o URL."""
    # Si es URL, extraer ID
    if "notebooklm.google.com" in partial_id:
        partial_id = partial_id.rstrip("/").split("/")[-1]

    # Si parece completo (UUID), devolverlo
    if len(partial_id) == 36 and partial_id.count("-") == 4:
        return partial_id

    # Buscar en library por prefijo
    library = _load_library()
    matches = [nid for nid in library["notebooks"] if nid.startswith(partial_id)]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        print(f"ERROR: ID ambiguo '{partial_id}' coincide con {len(matches)} notebooks")
        sys.exit(1)

    # Devolver tal cual (puede ser ID completo no en library)
    return partial_id


def _get_active_id() -> str | None:
    """Obtiene el ID del notebook activo."""
    library = _load_library()
    return library.get("active_notebook_id")


def main():
    parser = argparse.ArgumentParser(description="Gestión de notebooks NotebookLM")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Listar notebooks")
    sub.add_parser("sync", help="Sincronizar library.json con API")

    p_create = sub.add_parser("create", help="Crear notebook")
    p_create.add_argument("--name", required=True, help="Nombre del notebook")

    p_delete = sub.add_parser("delete", help="Eliminar notebook")
    p_delete.add_argument("--id", required=True, help="ID del notebook")

    p_get = sub.add_parser("get", help="Detalles de un notebook")
    p_get.add_argument("--id", required=True, help="ID del notebook")

    p_activate = sub.add_parser("activate", help="Activar notebook")
    p_activate.add_argument("--id", required=True, help="ID del notebook")

    args = parser.parse_args()

    if args.command == "list":
        sys.exit(cmd_list())
    elif args.command == "sync":
        sys.exit(cmd_sync())
    elif args.command == "create":
        sys.exit(cmd_create(args.name))
    elif args.command == "delete":
        sys.exit(cmd_delete(args.id))
    elif args.command == "get":
        sys.exit(cmd_get(args.id))
    elif args.command == "activate":
        sys.exit(cmd_activate(args.id))


if __name__ == "__main__":
    main()
