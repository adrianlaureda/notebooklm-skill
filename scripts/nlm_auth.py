#!/usr/bin/env python3
"""
Gestión de autenticación para notebooklm-py.
Comandos: check, setup, migrate, validate
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from nlm_client import NLM_HOME, LEGACY_STATE, _get_storage_path, _create_client, run_async


def cmd_check():
    """Comprueba si hay auth válida disponible."""
    path = _get_storage_path()
    if path is None:
        print("NO AUTH: No se encontró storage_state.json")
        print("  Rutas buscadas:")
        print(f"    - {NLM_HOME / 'storage_state.json'}")
        print(f"    - {LEGACY_STATE}")
        print("  Ejecuta: python scripts/run.py nlm_auth.py setup")
        return 1

    print(f"AUTH ENCONTRADA: {path}")

    # Verificar que el JSON es válido
    try:
        data = json.loads(path.read_text())
        cookies = data.get("cookies", [])
        cookie_names = {c.get("name", "") for c in cookies}
        required = {"SID", "HSID", "SSID"}
        missing = required - cookie_names
        if missing:
            print(f"  AVISO: Faltan cookies requeridas: {missing}")
            return 1
        print(f"  Cookies: {len(cookies)} ({', '.join(sorted(cookie_names & required))}... OK)")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ERROR: JSON inválido: {e}")
        return 1

    return 0


def cmd_validate():
    """Valida auth haciendo una llamada real a la API (lista notebooks)."""

    async def _validate():
        try:
            async with await _create_client() as client:
                notebooks = await client.notebooks.list()
                print(f"AUTH VÁLIDA: {len(notebooks)} notebooks accesibles")
                for nb in notebooks[:5]:
                    print(f"  - {nb.title}")
                if len(notebooks) > 5:
                    print(f"  ... y {len(notebooks) - 5} más")
                return 0
        except Exception as e:
            print(f"AUTH INVÁLIDA: {e}")
            print("  Ejecuta: python scripts/run.py nlm_auth.py setup")
            return 1

    return run_async(_validate())


def cmd_migrate():
    """Migra auth de legacy (Patchright) a notebooklm-py (~/.notebooklm/)."""
    native = NLM_HOME / "storage_state.json"

    if native.exists():
        print(f"Ya existe auth nativa: {native}")
        print("  Usa --force para sobreescribir")
        return 0

    if not LEGACY_STATE.exists():
        print(f"No hay auth legacy en: {LEGACY_STATE}")
        print("  Ejecuta: python scripts/run.py nlm_auth.py setup")
        return 1

    # Crear directorio y copiar
    NLM_HOME.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LEGACY_STATE, native)
    print(f"Auth migrada: {LEGACY_STATE} → {native}")

    # Validar la copia
    print("Validando auth migrada...")
    return cmd_validate()


def cmd_setup():
    """Ejecuta notebooklm login (abre navegador para login de Google)."""
    print("Abriendo navegador para login de Google...")
    print("  Inicia sesión con tu cuenta de Google en la ventana que se abre.")

    # Buscar el CLI dentro del venv del skill
    from nlm_client import SKILL_DIR
    venv_bin = SKILL_DIR / ".venv" / "bin" / "notebooklm"
    cli_cmd = str(venv_bin) if venv_bin.exists() else "notebooklm"

    try:
        result = subprocess.run(
            [cli_cmd, "login"],
            check=False
        )
        if result.returncode == 0:
            print("Login completado.")
            return cmd_validate()
        else:
            print(f"Login falló (código {result.returncode})")
            return 1
    except FileNotFoundError:
        print(f"ERROR: Comando 'notebooklm' no encontrado en: {cli_cmd}")
        print("  Asegúrate de que notebooklm-py está instalado:")
        print("  .venv/bin/pip install 'notebooklm-py[browser]'")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Gestión de auth NotebookLM")
    parser.add_argument(
        "command",
        choices=["check", "setup", "migrate", "validate"],
        help="check: buscar auth | setup: login | migrate: legacy→nativa | validate: test API"
    )
    parser.add_argument("--force", action="store_true", help="Sobreescribir auth existente")
    args = parser.parse_args()

    if args.command == "check":
        sys.exit(cmd_check())
    elif args.command == "setup":
        sys.exit(cmd_setup())
    elif args.command == "migrate":
        if args.force:
            native = NLM_HOME / "storage_state.json"
            if native.exists():
                native.unlink()
        sys.exit(cmd_migrate())
    elif args.command == "validate":
        sys.exit(cmd_validate())


if __name__ == "__main__":
    main()
