#!/usr/bin/env python3
"""
Wrapper síncrono sobre la API async de notebooklm-py.
Cada script nlm_* importa get_client() para obtener un cliente configurado.
"""

import asyncio
import sys
from pathlib import Path

# Rutas de autenticación (en orden de prioridad)
NLM_HOME = Path.home() / ".notebooklm"
SKILL_DIR = Path(__file__).parent.parent
LEGACY_STATE = SKILL_DIR / "data" / "browser_state" / "state.json"


def _get_storage_path() -> Path | None:
    """Busca storage_state.json en las rutas conocidas."""
    # 1. Ruta nativa de notebooklm-py
    native = NLM_HOME / "storage_state.json"
    if native.exists():
        return native
    # 2. Ruta legacy del skill
    if LEGACY_STATE.exists():
        return LEGACY_STATE
    return None


async def _create_client(storage_path: Path | None = None):
    """Crea un cliente async de NotebookLM."""
    from notebooklm import NotebookLMClient

    path = storage_path or _get_storage_path()
    if path is None:
        print("ERROR: No se encontró storage_state.json", file=sys.stderr)
        print("  Ejecuta: python scripts/run.py nlm_auth.py setup", file=sys.stderr)
        sys.exit(1)

    return await NotebookLMClient.from_storage(str(path))


def run_async(coro):
    """Ejecuta una corrutina de forma síncrona. Punto de entrada para todos los scripts nlm_*."""
    return asyncio.run(coro)
