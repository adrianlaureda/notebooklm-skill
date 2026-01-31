#!/usr/bin/env python3
"""
Añade un cuaderno de forma interactiva (más fácil que el CLI)
Uso: python3 add_notebook_simple.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR

LIBRARY_FILE = DATA_DIR / "library.json"

def load_library():
    if LIBRARY_FILE.exists():
        with open(LIBRARY_FILE) as f:
            return json.load(f)
    return {"notebooks": []}

def save_library(data):
    LIBRARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LIBRARY_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    print("\n📚 Añadir cuaderno a NotebookLM Skill")
    print("="*50)

    # Pedir URL
    print("\nPega la URL del cuaderno (o 'q' para salir):")
    url = input("> ").strip()

    if url.lower() == 'q':
        return

    # Validar URL
    if "/notebook/" not in url:
        print("❌ URL inválida. Debe contener '/notebook/'")
        return

    # Extraer ID
    try:
        nb_id = url.split("/notebook/")[-1].split("?")[0].split("/")[0]
    except:
        print("❌ No se pudo extraer el ID del cuaderno")
        return

    # Normalizar URL
    clean_url = f"https://notebooklm.google.com/notebook/{nb_id}"

    # Pedir nombre
    print("\nNombre del cuaderno:")
    name = input("> ").strip() or f"Cuaderno {nb_id[:8]}"

    # Pedir descripción (opcional)
    print("\nDescripción breve (Enter para omitir):")
    description = input("> ").strip() or f"Cuaderno de NotebookLM: {name}"

    # Pedir temas
    print("\nTemas separados por coma (ej: biología,ciencia):")
    topics_input = input("> ").strip()
    topics = [t.strip() for t in topics_input.split(",")] if topics_input else ["general"]

    # Crear entrada
    notebook = {
        "id": nb_id,
        "name": name,
        "url": clean_url,
        "description": description,
        "topics": topics,
        "use_cases": ["consulta", "investigación"],
        "tags": topics
    }

    # Guardar
    library = load_library()

    # Verificar duplicados
    existing_ids = [nb["id"] for nb in library.get("notebooks", [])]
    if nb_id in existing_ids:
        print(f"\n⚠️  Este cuaderno ya existe en la biblioteca")
        return

    library.setdefault("notebooks", []).append(notebook)
    save_library(library)

    print(f"\n✅ Cuaderno añadido: {name}")
    print(f"   URL: {clean_url}")
    print(f"   Temas: {', '.join(topics)}")
    print(f"\n💾 Guardado en: {LIBRARY_FILE}")

    # Preguntar si añadir otro
    print("\n¿Añadir otro cuaderno? (s/n)")
    if input("> ").strip().lower() == 's':
        main()

if __name__ == "__main__":
    main()
