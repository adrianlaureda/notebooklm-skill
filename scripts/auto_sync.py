#!/usr/bin/env python3
"""
Sincronización automática condicional de cuadernos.
Solo sincroniza si pasaron más de X horas desde la última vez.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR

SYNC_INTERVAL_HOURS = 24  # Sincronizar cada 24 horas


def should_sync():
    """
    Verifica si es necesario sincronizar basándose en el tiempo transcurrido.

    Returns:
        True si pasaron más de SYNC_INTERVAL_HOURS desde la última sincronización
    """
    library_file = DATA_DIR / "library.json"

    if not library_file.exists():
        return True

    try:
        with open(library_file) as f:
            library = json.load(f)

        last_sync = library.get("last_sync")
        if not last_sync:
            return True

        last_sync_time = datetime.fromisoformat(last_sync)
        elapsed = datetime.now() - last_sync_time

        return elapsed > timedelta(hours=SYNC_INTERVAL_HOURS)
    except:
        return True


def update_sync_timestamp():
    """Actualiza el timestamp de última sincronización."""
    library_file = DATA_DIR / "library.json"

    if library_file.exists():
        with open(library_file) as f:
            library = json.load(f)
    else:
        library = {"notebooks": {}, "active_notebook_id": None}

    library["last_sync"] = datetime.now().isoformat()

    with open(library_file, 'w') as f:
        json.dump(library, f, indent=2, ensure_ascii=False)


def auto_sync_if_needed(force=False):
    """
    Sincroniza cuadernos si es necesario.

    Args:
        force: Si True, sincroniza sin importar el tiempo transcurrido

    Returns:
        Dict con resultado de la operación
    """
    if not force and not should_sync():
        return {
            "status": "skipped",
            "message": "Sincronización no necesaria (última: < 24h)"
        }

    # Importar aquí para evitar cargar patchright si no es necesario
    from scan_notebooks import sync_notebooks

    print("🔄 Sincronizando cuadernos de NotebookLM...")
    result = sync_notebooks(headless=True)

    if result["status"] == "ok":
        update_sync_timestamp()

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sincronización automática de cuadernos")
    parser.add_argument("--force", action="store_true", help="Forzar sincronización")
    parser.add_argument("--check", action="store_true", help="Solo verificar si es necesario")
    args = parser.parse_args()

    if args.check:
        needs_sync = should_sync()
        print(f"¿Necesita sincronización?: {'Sí' if needs_sync else 'No'}")
        return

    result = auto_sync_if_needed(force=args.force)

    if result["status"] == "ok":
        print(f"✅ {result.get('message', 'Sincronizado')}")
    elif result["status"] == "skipped":
        print(f"⏭️  {result['message']}")
    else:
        print(f"⚠️  {result.get('message', 'Error')}")


if __name__ == "__main__":
    main()
