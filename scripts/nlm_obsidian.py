#!/usr/bin/env python3
"""
Guardar resultados de NotebookLM en el vault de Obsidian.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

VAULT_PATH = Path.home() / "Documents" / "AdrianLaureda"


def save_to_obsidian(notebook_id: str, notebook_name: str,
                     questions_results: list[dict] = None,
                     downloads: list[str] = None,
                     output_path: str = None):
    """Crea una nota en Obsidian con los resultados del análisis."""
    # Ruta de la nota
    if output_path:
        note_path = VAULT_PATH / output_path
    else:
        note_path = VAULT_PATH / "NotebookLM" / f"{notebook_name}.md"

    # Asegurar directorio
    note_path.parent.mkdir(parents=True, exist_ok=True)

    # Construir contenido
    lines = []

    # Frontmatter
    lines.append("---")
    lines.append(f"source: notebooklm")
    lines.append(f"notebook_id: {notebook_id}")
    lines.append(f"notebook_name: \"{notebook_name}\"")
    lines.append(f"created: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"url: https://notebooklm.google.com/notebook/{notebook_id}")
    lines.append("---")
    lines.append("")

    # Título
    lines.append(f"# {notebook_name}")
    lines.append("")
    lines.append(f"> Generado con NotebookLM el {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Queries
    if questions_results:
        lines.append("## Preguntas y respuestas")
        lines.append("")
        for qr in questions_results:
            lines.append(f"### {qr['question']}")
            lines.append("")
            lines.append(qr["answer"])
            lines.append("")

    # Descargas
    if downloads:
        lines.append("## Archivos generados")
        lines.append("")
        for dl in downloads:
            dl_path = Path(dl)
            lines.append(f"- [[{dl_path.name}]] ({dl_path.suffix[1:].upper()})")
        lines.append("")

    # Enlace al notebook
    lines.append("## Enlaces")
    lines.append("")
    lines.append(f"- [Abrir en NotebookLM](https://notebooklm.google.com/notebook/{notebook_id})")
    lines.append("")

    # Escribir
    note_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"OBSIDIAN: Nota guardada en {note_path}")
    return str(note_path)


def main():
    parser = argparse.ArgumentParser(description="Guardar en Obsidian")
    parser.add_argument("--notebook-id", required=True, help="ID del notebook")
    parser.add_argument("--notebook-name", required=True, help="Nombre del notebook")
    parser.add_argument("--output", help="Ruta relativa en vault")
    parser.add_argument("--answer", action="append", default=[], help="Respuestas Q:A (formato 'pregunta|||respuesta')")
    parser.add_argument("--download", action="append", default=[], help="Rutas de archivos descargados")

    args = parser.parse_args()

    # Parsear respuestas
    qr = []
    for a in args.answer:
        if "|||" in a:
            q, r = a.split("|||", 1)
            qr.append({"question": q, "answer": r})

    save_to_obsidian(
        notebook_id=args.notebook_id,
        notebook_name=args.notebook_name,
        questions_results=qr or None,
        downloads=args.download or None,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
