#!/usr/bin/env python3
"""
Orquestador de pipeline completo: fuentes → notebook → queries → studio → obsidian.
"""

import argparse
import sys

from nlm_client import _create_client, run_async


def cmd_pipeline(name: str, sources: list[str], questions: list[str] = None,
                 studio_types: list[str] = None, obsidian_path: str = None,
                 language: str = "es"):
    """Pipeline completo: crear notebook, añadir fuentes, queries, studio, obsidian."""

    async def _pipeline():
        # 1. Verificar auth
        from nlm_auth import cmd_check
        if cmd_check() != 0:
            print("\nERROR: Auth no válida. Ejecuta: python scripts/run.py nlm_auth.py setup")
            return 1

        async with await _create_client() as client:
            # 2. Crear notebook
            print(f"\n=== CREAR NOTEBOOK: {name} ===")
            nb = await client.notebooks.create(name)
            print(f"  ID: {nb.id}")

            # Sincronizar library.json
            from nlm_notebook import _load_library, _save_library, _nb_to_entry
            library = _load_library()
            library["notebooks"][nb.id] = _nb_to_entry(nb)
            library["active_notebook_id"] = nb.id
            _save_library(library)

            # 3. Añadir fuentes
            if sources:
                print(f"\n=== AÑADIR {len(sources)} FUENTES ===")
                from nlm_sources import add_source
                ok, fail = 0, 0
                for src in sources:
                    result = await add_source(client, nb.id, src)
                    if result:
                        ok += 1
                    else:
                        fail += 1
                print(f"  Resultado: {ok} OK, {fail} errores")

            # 4. Queries
            results = []
            if questions:
                print(f"\n=== QUERIES ({len(questions)}) ===")
                for q in questions:
                    print(f"\n  Q: {q}")
                    result = await client.chat.ask(nb.id, q)
                    print(f"  A: {result.answer[:300]}...")
                    results.append({"question": q, "answer": result.answer})

            # 5. Studio
            downloads = []
            if studio_types:
                print(f"\n=== STUDIO ({len(studio_types)}) ===")
                from nlm_studio import STUDIO_TYPES, OUTPUTS_DIR
                OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

                for stype in studio_types:
                    if stype not in STUDIO_TYPES:
                        print(f"  AVISO: Tipo desconocido '{stype}', saltando")
                        continue

                    type_info = STUDIO_TYPES[stype]
                    generate_fn = getattr(client.artifacts, type_info["generate"])

                    print(f"\n  Generando {stype}...")
                    try:
                        # Solo pasar language si el método lo acepta
                        supports_lang = {"audio", "video", "report", "slide_deck", "infographic", "data_table"}
                        kwargs = {"language": language} if stype in supports_lang else {}
                        status = await generate_fn(nb.id, **kwargs)

                        if stype == "mind_map":
                            output_path = OUTPUTS_DIR / f"{nb.id[:8]}_{stype}.{type_info['ext']}"
                            await client.artifacts.download_mind_map(nb.id, str(output_path))
                            downloads.append(str(output_path))
                            print(f"  Descargado: {output_path}")
                            continue

                        final = await client.artifacts.wait_for_completion(
                            nb.id, status.task_id, timeout=300, poll_interval=5
                        )
                        if final.is_complete:
                            output_path = OUTPUTS_DIR / f"{nb.id[:8]}_{stype}.{type_info['ext']}"
                            download_fn = getattr(client.artifacts, type_info["download"])
                            await download_fn(nb.id, str(output_path))
                            downloads.append(str(output_path))
                            print(f"  Descargado: {output_path}")
                        else:
                            print(f"  ERROR: {stype} no se completó")
                    except Exception as e:
                        print(f"  ERROR generando {stype}: {e}")

            # 6. Obsidian
            if obsidian_path:
                print(f"\n=== GUARDAR EN OBSIDIAN ===")
                from nlm_obsidian import save_to_obsidian
                save_to_obsidian(
                    notebook_id=nb.id,
                    notebook_name=name,
                    questions_results=results,
                    downloads=downloads,
                    output_path=obsidian_path,
                )

            # Resumen
            print(f"\n=== RESUMEN ===")
            print(f"  Notebook: {name} [{nb.id[:8]}...]")
            print(f"  Fuentes: {len(sources)}")
            if questions:
                print(f"  Queries: {len(questions)}")
            if downloads:
                print(f"  Descargas: {len(downloads)}")
            if obsidian_path:
                print(f"  Obsidian: {obsidian_path}")

            return 0

    return run_async(_pipeline())


def main():
    parser = argparse.ArgumentParser(description="Pipeline completo NotebookLM")
    parser.add_argument("--name", required=True, help="Nombre del notebook")
    parser.add_argument("--source", "-s", action="append", default=[], help="Fuentes (repetible)")
    parser.add_argument("--question", "-q", action="append", default=[], help="Preguntas (repetible)")
    parser.add_argument("--studio", "-t", action="append", default=[],
                        help="Tipos de Studio a generar (repetible)")
    parser.add_argument("--obsidian", help="Ruta en vault de Obsidian para guardar resultados")
    parser.add_argument("--language", "-l", default="es", help="Idioma (default: es)")

    args = parser.parse_args()

    if not args.source:
        print("ERROR: Se necesita al menos una fuente (--source)")
        sys.exit(1)

    sys.exit(cmd_pipeline(
        name=args.name,
        sources=args.source,
        questions=args.question or None,
        studio_types=args.studio or None,
        obsidian_path=args.obsidian,
        language=args.language,
    ))


if __name__ == "__main__":
    main()
