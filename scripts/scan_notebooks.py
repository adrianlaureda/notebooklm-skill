#!/usr/bin/env python3
"""
Escanea cuadernos de NotebookLM interceptando peticiones de red.
Captura respuestas de batchexecute y extrae nombre + UUID de cada cuaderno.
"""

import json
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR, BROWSER_STATE_DIR

def scan_notebooks(headless=False, auto_save=False):
    """
    Escanea cuadernos de NotebookLM extrayendo del DOM.

    Args:
        headless: Si True, ejecuta sin ventana visible
        auto_save: Si True, guarda automáticamente sin preguntar

    Returns:
        Lista de diccionarios con id, name, url de cada cuaderno
    """
    from patchright.sync_api import sync_playwright

    state_file = BROWSER_STATE_DIR / "state.json"
    profile_dir = BROWSER_STATE_DIR / "browser_profile"

    if not state_file.exists():
        print("❌ No hay sesión autenticada")
        return []

    print("🔍 Escaneando cuadernos...")

    notebooks = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # Cargar cookies de sesión
        with open(state_file, 'r') as f:
            state = json.load(f)
            context.add_cookies(state.get('cookies', []))

        page = context.new_page()

        try:
            print("  🌐 Navegando...")
            page.goto("https://notebooklm.google.com", wait_until="networkidle", timeout=45000)

            if "accounts.google.com" in page.url:
                print("❌ Sesión expirada - necesitas re-autenticar")
                return []

            print("  ⏳ Esperando carga completa...")
            time.sleep(4)

            # Scroll para cargar más cuadernos
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

            # Extraer HTML
            html = page.content()

            # Patrón: id="project-UUID-title"> NOMBRE </span>
            # NotebookLM usa Angular y renderiza cuadernos con este formato
            pattern = r'id="project-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})-title">\s*([^<]+?)\s*</span>'
            matches = re.findall(pattern, html)

            print(f"  📋 Encontrados {len(matches)} cuadernos en el DOM")

            seen_ids = set()
            for nb_id, name in matches:
                if nb_id not in seen_ids:
                    seen_ids.add(nb_id)
                    clean_name = name.strip()
                    if clean_name and len(clean_name) > 2:
                        notebooks.append({
                            "id": nb_id,
                            "name": clean_name,
                            "url": f"https://notebooklm.google.com/notebook/{nb_id}"
                        })

            # Guardar HTML para debug
            debug_file = DATA_DIR / "last_scan_html.html"
            with open(debug_file, 'w') as f:
                f.write(html)

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            context.close()

    return notebooks


def save_to_library(notebooks):
    """
    Guarda los cuadernos en la biblioteca del skill.
    Usa formato dict por ID para compatibilidad con notebook_manager.py.

    Returns:
        Tupla (añadidos, actualizados)
    """
    library_file = DATA_DIR / "library.json"
    today = date.today().isoformat()

    if library_file.exists():
        with open(library_file) as f:
            library = json.load(f)
    else:
        library = {"notebooks": {}, "active_notebook_id": None}

    # Asegurar formato dict (migrar si es lista antigua)
    if isinstance(library.get("notebooks"), list):
        old_list = library["notebooks"]
        library["notebooks"] = {nb["id"]: nb for nb in old_list}

    existing = library.get("notebooks", {})
    added = 0
    updated = 0

    for nb in notebooks:
        nb_id = nb["id"]
        if nb_id not in existing:
            # Nuevo cuaderno
            existing[nb_id] = {
                "id": nb_id,
                "name": nb["name"],
                "url": nb["url"],
                "description": f"Cuaderno: {nb['name']}",
                "topics": ["general"],
                "use_cases": ["consulta"],
                "tags": [],
                "use_count": 0,
                "added_at": today,
                "last_used": None
            }
            added += 1
        else:
            # Actualizar nombre si cambió
            if existing[nb_id].get("name") != nb["name"]:
                existing[nb_id]["name"] = nb["name"]
                existing[nb_id]["description"] = f"Cuaderno: {nb['name']}"
                updated += 1

    library["notebooks"] = existing
    with open(library_file, 'w') as f:
        json.dump(library, f, indent=2, ensure_ascii=False)

    return added, updated


def sync_notebooks(headless=True):
    """
    Sincroniza cuadernos automáticamente (para uso en hooks).
    Ejecuta en headless y guarda sin preguntar.

    Returns:
        Diccionario con resultado de la sincronización
    """
    notebooks = scan_notebooks(headless=headless, auto_save=True)

    if not notebooks:
        return {"status": "error", "message": "No se encontraron cuadernos o sesión expirada"}

    added, updated = save_to_library(notebooks)

    return {
        "status": "ok",
        "total": len(notebooks),
        "added": added,
        "updated": updated,
        "notebooks": [nb["name"] for nb in notebooks]
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Escanea cuadernos de NotebookLM")
    parser.add_argument("--auto", action="store_true", help="Sincronizar automáticamente sin preguntar")
    parser.add_argument("--headless", action="store_true", help="Ejecutar sin ventana visible")
    args = parser.parse_args()

    if args.auto:
        # Modo automático (para hooks)
        result = sync_notebooks(headless=args.headless)
        if result["status"] == "ok":
            print(f"✅ Sincronizados {result['total']} cuadernos (+{result['added']} nuevos, ~{result['updated']} actualizados)")
        else:
            print(f"⚠️  {result['message']}")
        return

    # Modo interactivo
    notebooks = scan_notebooks(headless=args.headless)

    if notebooks:
        print(f"\n{'='*60}")
        print(f"📚 CUADERNOS ENCONTRADOS ({len(notebooks)})")
        print('='*60)

        for i, nb in enumerate(notebooks, 1):
            print(f"  {i}. {nb['name']}")
            print(f"     {nb['url']}")

        print(f"\n¿Añadir todos a la biblioteca? (s/n)")
        resp = input("> ").strip().lower()

        if resp == 's':
            added, updated = save_to_library(notebooks)
            print(f"\n✅ Añadidos {added} cuadernos nuevos, {updated} actualizados")
        else:
            output = DATA_DIR / "scanned_notebooks.json"
            with open(output, 'w') as f:
                json.dump(notebooks, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Lista guardada en: {output}")
    else:
        print("\n📭 No se encontraron cuadernos.")


if __name__ == "__main__":
    main()
