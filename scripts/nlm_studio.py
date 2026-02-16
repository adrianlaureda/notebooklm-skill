#!/usr/bin/env python3
"""
Generación y descarga de contenido Studio de NotebookLM.
Tipos: audio, video, quiz, flashcards, report, slide_deck, infographic, data_table, mind_map
"""

import argparse
import sys
from pathlib import Path

from nlm_client import _create_client, run_async

SKILL_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = SKILL_DIR / "data" / "outputs"


# Mapeo de tipos a métodos de generación y descarga
STUDIO_TYPES = {
    "audio": {"generate": "generate_audio", "download": "download_audio", "ext": "mp3"},
    "video": {"generate": "generate_video", "download": "download_video", "ext": "mp4"},
    "quiz": {"generate": "generate_quiz", "download": "download_quiz", "ext": "json"},
    "flashcards": {"generate": "generate_flashcards", "download": "download_flashcards", "ext": "json"},
    "report": {"generate": "generate_report", "download": "download_report", "ext": "md"},
    "slide_deck": {"generate": "generate_slide_deck", "download": "download_slide_deck", "ext": "pdf"},
    "infographic": {"generate": "generate_infographic", "download": "download_infographic", "ext": "png"},
    "data_table": {"generate": "generate_data_table", "download": "download_data_table", "ext": "csv"},
    "mind_map": {"generate": "generate_mind_map", "download": "download_mind_map", "ext": "json"},
}


def _build_generate_kwargs(studio_type: str, args) -> dict:
    """Construye kwargs para el método de generación según el tipo.

    Firmas reales de la API (verificadas por introspección):
      audio:       source_ids, language, instructions, audio_format, audio_length
      video:       source_ids, language, instructions, video_format, video_style
      quiz:        source_ids, instructions, quantity, difficulty
      flashcards:  source_ids, instructions, quantity, difficulty
      report:      report_format, source_ids, language, custom_prompt
      slide_deck:  source_ids, language, instructions, slide_format, slide_length
      infographic: source_ids, language, instructions, orientation, detail_level
      data_table:  source_ids, language, instructions
      mind_map:    source_ids
    """
    kwargs = {}

    # source_ids: todos los tipos lo aceptan
    if args.source_ids:
        kwargs["source_ids"] = args.source_ids

    # language: solo audio, video, report, slide_deck, infographic, data_table
    SUPPORTS_LANGUAGE = {"audio", "video", "report", "slide_deck", "infographic", "data_table"}
    if args.language and studio_type in SUPPORTS_LANGUAGE:
        kwargs["language"] = args.language

    # instructions: todos excepto report (usa custom_prompt) y mind_map
    SUPPORTS_INSTRUCTIONS = {"audio", "video", "quiz", "flashcards", "slide_deck", "infographic", "data_table"}
    if args.instructions and studio_type in SUPPORTS_INSTRUCTIONS:
        kwargs["instructions"] = args.instructions

    # Parámetros específicos por tipo
    if studio_type == "audio":
        if args.format:
            from notebooklm import AudioFormat
            fmt_map = {"deep_dive": AudioFormat.DEEP_DIVE, "brief": AudioFormat.BRIEF,
                       "critique": AudioFormat.CRITIQUE, "debate": AudioFormat.DEBATE}
            kwargs["audio_format"] = fmt_map.get(args.format, AudioFormat.DEEP_DIVE)
        if args.length:
            from notebooklm import AudioLength
            len_map = {"short": AudioLength.SHORT, "default": AudioLength.DEFAULT, "long": AudioLength.LONG}
            kwargs["audio_length"] = len_map.get(args.length, AudioLength.DEFAULT)

    elif studio_type == "video":
        if args.format:
            from notebooklm import VideoFormat
            fmt_map = {"explainer": VideoFormat.EXPLAINER, "brief": VideoFormat.BRIEF}
            kwargs["video_format"] = fmt_map.get(args.format, VideoFormat.EXPLAINER)
        if args.style:
            from notebooklm import VideoStyle
            style_map = {
                "auto": VideoStyle.AUTO_SELECT, "classic": VideoStyle.CLASSIC,
                "whiteboard": VideoStyle.WHITEBOARD, "kawaii": VideoStyle.KAWAII,
                "anime": VideoStyle.ANIME, "watercolor": VideoStyle.WATERCOLOR,
            }
            kwargs["video_style"] = style_map.get(args.style, VideoStyle.AUTO_SELECT)

    elif studio_type in ("quiz", "flashcards"):
        if args.difficulty:
            from notebooklm import QuizDifficulty
            diff_map = {"easy": QuizDifficulty.EASY, "medium": QuizDifficulty.MEDIUM, "hard": QuizDifficulty.HARD}
            kwargs["difficulty"] = diff_map.get(args.difficulty, QuizDifficulty.MEDIUM)
        if args.quantity:
            from notebooklm import QuizQuantity
            qty_map = {"fewer": QuizQuantity.FEWER, "standard": QuizQuantity.STANDARD}
            kwargs["quantity"] = qty_map.get(args.quantity, QuizQuantity.STANDARD)

    elif studio_type == "report":
        if args.instructions:
            kwargs["custom_prompt"] = args.instructions
        if args.format:
            from notebooklm import ReportFormat
            fmt_map = {"briefing": ReportFormat.BRIEFING_DOC, "study_guide": ReportFormat.STUDY_GUIDE,
                       "blog": ReportFormat.BLOG_POST, "custom": ReportFormat.CUSTOM}
            kwargs["report_format"] = fmt_map.get(args.format, ReportFormat.STUDY_GUIDE)

    elif studio_type == "slide_deck":
        if args.format:
            from notebooklm import SlideDeckFormat
            fmt_map = {"detailed_deck": SlideDeckFormat.DETAILED_DECK, "presenter_slides": SlideDeckFormat.PRESENTER_SLIDES}
            kwargs["slide_format"] = fmt_map.get(args.format, SlideDeckFormat.DETAILED_DECK)
        if args.length:
            from notebooklm import SlideDeckLength
            len_map = {"default": SlideDeckLength.DEFAULT, "short": SlideDeckLength.SHORT}
            kwargs["slide_length"] = len_map.get(args.length, SlideDeckLength.DEFAULT)

    elif studio_type == "infographic":
        # orientation y detail_level se exponen como --format y --style
        pass

    elif studio_type == "data_table":
        # instructions ya se maneja arriba
        pass

    return kwargs


def cmd_generate(notebook_id: str, studio_type: str, args, download: bool = True):
    """Genera contenido Studio y opcionalmente lo descarga."""

    async def _generate():
        type_info = STUDIO_TYPES[studio_type]
        async with await _create_client() as client:
            artifacts = client.artifacts
            generate_fn = getattr(artifacts, type_info["generate"])
            kwargs = _build_generate_kwargs(studio_type, args)

            print(f"GENERANDO {studio_type}...")
            status = await generate_fn(notebook_id, **kwargs)

            # Mind map es síncrono, retorna resultado directo
            if studio_type == "mind_map":
                print(f"MIND MAP generado")
                if download:
                    output_path = _output_path(notebook_id, studio_type, type_info["ext"], args.output)
                    await artifacts.download_mind_map(notebook_id, str(output_path))
                    print(f"DESCARGADO: {output_path}")
                return 0

            # Esperar a que termine
            task_id = status.task_id
            print(f"  Task ID: {task_id}")
            print(f"  Esperando (timeout {args.timeout}s)...")

            final = await artifacts.wait_for_completion(
                notebook_id, task_id,
                timeout=args.timeout,
                initial_interval=args.poll_interval,
            )

            if final.is_complete:
                print(f"COMPLETADO: {studio_type}")
            else:
                print(f"TIMEOUT o ERROR: estado final no completado")
                return 1

            # Descargar si se pide
            if download:
                output_path = _output_path(notebook_id, studio_type, type_info["ext"], args.output)
                download_fn = getattr(artifacts, type_info["download"])

                # Quiz y flashcards aceptan output_format
                download_kwargs = {}
                if studio_type in ("quiz", "flashcards") and args.output_format:
                    download_kwargs["output_format"] = args.output_format
                    if args.output_format == "markdown":
                        output_path = output_path.with_suffix(".md")
                    elif args.output_format == "html":
                        output_path = output_path.with_suffix(".html")

                await download_fn(notebook_id, str(output_path), **download_kwargs)
                print(f"DESCARGADO: {output_path}")

            return 0

    return run_async(_generate())


def cmd_list_artifacts(notebook_id: str, studio_type: str = None):
    """Lista artefactos generados de un notebook."""

    async def _list():
        async with await _create_client() as client:
            if studio_type:
                list_fn_name = f"list_{studio_type}" if studio_type != "audio" else "list_audio"
                # Nombres especiales
                special_names = {
                    "quiz": "list_quizzes", "flashcards": "list_flashcards",
                    "report": "list_reports", "infographic": "list_infographics",
                    "slide_deck": "list_slide_decks", "data_table": "list_data_tables",
                    "audio": "list_audio", "video": "list_video",
                }
                list_fn = getattr(client.artifacts, special_names.get(studio_type, list_fn_name))
                items = await list_fn(notebook_id)
            else:
                items = await client.artifacts.list(notebook_id)

            print(f"ARTEFACTOS ({len(items)}):")
            for item in items:
                status_str = "OK" if getattr(item, "is_completed", False) else "procesando"
                kind = getattr(item, "kind", "?")
                title = getattr(item, "title", "(sin título)")
                print(f"  [{item.id[:8]}...] [{kind}] {title} ({status_str})")
            return 0

    return run_async(_list())


def _output_path(notebook_id: str, studio_type: str, ext: str, custom_path: str = None) -> Path:
    """Genera ruta de salida para descargas."""
    if custom_path:
        return Path(custom_path).expanduser()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUTS_DIR / f"{notebook_id[:8]}_{studio_type}.{ext}"


def main():
    parser = argparse.ArgumentParser(description="Studio de NotebookLM")
    sub = parser.add_subparsers(dest="command", required=True)

    # Generar
    p_gen = sub.add_parser("generate", help="Generar contenido Studio")
    p_gen.add_argument("--notebook-id", "--id", help="ID del notebook")
    p_gen.add_argument("--type", "-t", required=True, choices=list(STUDIO_TYPES.keys()), help="Tipo de contenido")
    p_gen.add_argument("--instructions", "-i", help="Instrucciones de generación")
    p_gen.add_argument("--language", "-l", default="es", help="Idioma (default: es)")
    p_gen.add_argument("--source-ids", nargs="+", help="IDs de fuentes específicas")
    p_gen.add_argument("--no-download", action="store_true", help="No descargar automáticamente")
    p_gen.add_argument("--output", "-o", help="Ruta de salida personalizada")
    p_gen.add_argument("--timeout", type=int, default=300, help="Timeout en segundos (default: 300)")
    p_gen.add_argument("--poll-interval", type=int, default=5, help="Intervalo de polling (default: 5s)")
    # Parámetros específicos por tipo
    p_gen.add_argument("--format", help="Formato (audio: deep_dive/brief/critique/debate; video: explainer/brief; report: briefing/study_guide/blog)")
    p_gen.add_argument("--style", help="Estilo video (auto/classic/whiteboard/kawaii/anime/watercolor)")
    p_gen.add_argument("--length", help="Duración audio (short/default/long)")
    p_gen.add_argument("--difficulty", help="Dificultad quiz/flashcards (easy/medium/hard)")
    p_gen.add_argument("--quantity", help="Cantidad quiz/flashcards (fewer/standard)")
    p_gen.add_argument("--title", help="Título para reports")
    p_gen.add_argument("--description", help="Descripción para reports/data_table")
    p_gen.add_argument("--output-format", choices=["json", "markdown", "html"], default="json",
                       help="Formato de descarga para quiz/flashcards")

    # Listar artefactos
    p_list = sub.add_parser("list", help="Listar artefactos generados")
    p_list.add_argument("--notebook-id", "--id", required=True, help="ID del notebook")
    p_list.add_argument("--type", "-t", choices=list(STUDIO_TYPES.keys()), help="Filtrar por tipo")

    args = parser.parse_args()

    from nlm_notebook import _resolve_id, _get_active_id

    if args.command == "generate":
        nid = _resolve_id(args.notebook_id) if args.notebook_id else _get_active_id()
        if not nid:
            print("ERROR: Especifica --notebook-id o activa un notebook.")
            sys.exit(1)
        sys.exit(cmd_generate(nid, args.type, args, download=not args.no_download))
    elif args.command == "list":
        sys.exit(cmd_list_artifacts(_resolve_id(args.notebook_id), getattr(args, "type", None)))


if __name__ == "__main__":
    main()
