#!/usr/bin/env python3
"""
Gestión de fuentes: detección automática de tipo, añadir individuales y batch.
"""

import argparse
import re
import sys
from pathlib import Path

from nlm_client import _create_client, run_async

# Extensiones soportadas para archivos locales
FILE_EXTENSIONS = {
    ".pdf", ".docx", ".txt", ".md",
    ".png", ".jpg", ".jpeg",
    ".mp3", ".wav", ".m4a", ".mp4",
}

# Patrones de detección automática
YOUTUBE_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+"),
    re.compile(r"(?:https?://)?youtu\.be/[\w-]+"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+"),
]

DRIVE_PATTERNS = [
    re.compile(r"(?:https?://)?drive\.google\.com/"),
    re.compile(r"(?:https?://)?docs\.google\.com/"),
]


def detect_source_type(source: str) -> str:
    """
    Detecta automáticamente el tipo de fuente.
    Retorna: 'youtube', 'drive', 'url', 'file', 'text'
    """
    # YouTube
    for pattern in YOUTUBE_PATTERNS:
        if pattern.search(source):
            return "youtube"

    # Google Drive / Docs
    for pattern in DRIVE_PATTERNS:
        if pattern.search(source):
            return "drive"

    # URL genérica
    if source.startswith(("http://", "https://")):
        return "url"

    # Archivo local
    path = Path(source).expanduser()
    if path.exists() or path.suffix.lower() in FILE_EXTENSIONS:
        return "file"

    # Texto (>200 chars o no coincide con nada)
    if len(source) > 200:
        return "text"

    # Por defecto asumir URL si parece dominio, o texto si no
    if "." in source and " " not in source:
        return "url"

    return "text"


async def add_source(client, notebook_id: str, source: str, source_type: str = None, title: str = None):
    """Añade una fuente a un notebook, detectando tipo automáticamente."""
    stype = source_type or detect_source_type(source)

    try:
        if stype == "youtube":
            result = await client.sources.add_youtube(notebook_id, source)
            print(f"  YOUTUBE: {source} → {getattr(result, 'title', 'OK')}")

        elif stype == "url":
            # Asegurar https://
            url = source if source.startswith("http") else f"https://{source}"
            result = await client.sources.add_url(notebook_id, url)
            print(f"  URL: {url} → {getattr(result, 'title', 'OK')}")

        elif stype == "file":
            path = Path(source).expanduser().resolve()
            if not path.exists():
                print(f"  ERROR: Archivo no encontrado: {path}", file=sys.stderr)
                return None
            result = await client.sources.add_file(notebook_id, path)
            print(f"  ARCHIVO: {path.name} → {getattr(result, 'title', 'OK')}")

        elif stype == "text":
            text_title = title or source[:50].strip() + "..."
            result = await client.sources.add_text(notebook_id, text_title, source)
            print(f"  TEXTO: '{text_title}' → OK")

        elif stype == "drive":
            # Para Drive necesitamos extraer file_id de la URL
            file_id = _extract_drive_id(source)
            if not file_id:
                print(f"  ERROR: No se pudo extraer file_id de: {source}", file=sys.stderr)
                return None
            drive_title = title or f"Drive: {file_id[:12]}..."
            result = await client.sources.add_drive(
                notebook_id, file_id, drive_title,
                "application/vnd.google-apps.document"
            )
            print(f"  DRIVE: {file_id} → {getattr(result, 'title', 'OK')}")

        else:
            print(f"  ERROR: Tipo desconocido: {stype}", file=sys.stderr)
            return None

        return result

    except Exception as e:
        print(f"  ERROR añadiendo {stype} '{source[:60]}': {e}", file=sys.stderr)
        return None


def _extract_drive_id(url: str) -> str | None:
    """Extrae file_id de una URL de Google Drive/Docs."""
    patterns = [
        re.compile(r"/d/([a-zA-Z0-9_-]+)"),
        re.compile(r"id=([a-zA-Z0-9_-]+)"),
        re.compile(r"/document/d/([a-zA-Z0-9_-]+)"),
        re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)"),
        re.compile(r"/presentation/d/([a-zA-Z0-9_-]+)"),
    ]
    for p in patterns:
        m = p.search(url)
        if m:
            return m.group(1)
    return None


def cmd_add(notebook_id: str, sources: list[str], source_type: str = None, title: str = None):
    """Añade una o más fuentes a un notebook."""

    async def _add():
        async with await _create_client() as client:
            print(f"Añadiendo {len(sources)} fuente(s) a [{notebook_id[:8]}...]:")
            ok, fail = 0, 0
            for src in sources:
                result = await add_source(client, notebook_id, src, source_type, title)
                if result:
                    ok += 1
                else:
                    fail += 1
            print(f"\nRESULTADO: {ok} añadidas, {fail} errores")
            return 0 if fail == 0 else 1

    return run_async(_add())


def cmd_list(notebook_id: str):
    """Lista las fuentes de un notebook."""

    async def _list():
        async with await _create_client() as client:
            sources = await client.sources.list(notebook_id)
            print(f"FUENTES ({len(sources)}):")
            for src in sources:
                title = getattr(src, "title", None) or "(sin título)"
                kind = getattr(src, "kind", "?")
                print(f"  [{src.id[:8]}...] [{kind}] {title}")
            return 0

    return run_async(_list())


def cmd_detect(source: str):
    """Detecta el tipo de una fuente (para debug)."""
    stype = detect_source_type(source)
    print(f"TIPO DETECTADO: {stype}")
    print(f"  Input: {source[:100]}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Gestión de fuentes NotebookLM")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Añadir fuentes")
    p_add.add_argument("--notebook-id", "--id", required=True, help="ID del notebook")
    p_add.add_argument("--source", "-s", action="append", required=True, help="Fuente (URL, archivo, texto)")
    p_add.add_argument("--type", choices=["youtube", "url", "file", "text", "drive"], help="Forzar tipo")
    p_add.add_argument("--title", help="Título para fuentes de texto/drive")

    p_list = sub.add_parser("list", help="Listar fuentes de un notebook")
    p_list.add_argument("--notebook-id", "--id", required=True, help="ID del notebook")

    p_detect = sub.add_parser("detect", help="Detectar tipo de fuente")
    p_detect.add_argument("source", help="Fuente a analizar")

    args = parser.parse_args()

    if args.command == "add":
        # Resolver notebook ID
        from nlm_notebook import _resolve_id, _get_active_id
        nid = _resolve_id(args.notebook_id) if args.notebook_id != "active" else _get_active_id()
        if not nid:
            print("ERROR: No hay notebook activo. Usa --notebook-id o activa uno.")
            sys.exit(1)
        sys.exit(cmd_add(nid, args.source, args.type, args.title))
    elif args.command == "list":
        from nlm_notebook import _resolve_id
        nid = _resolve_id(args.notebook_id)
        sys.exit(cmd_list(nid))
    elif args.command == "detect":
        sys.exit(cmd_detect(args.source))


if __name__ == "__main__":
    main()
