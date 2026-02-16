#!/usr/bin/env python3
"""
Consultas a notebooks con citas. Reemplaza ask_question.py (legacy).
"""

import argparse
import json
import sys

from nlm_client import _create_client, run_async


def cmd_ask(notebook_id: str, question: str, source_ids: list[str] = None, follow_up: str = None):
    """Hace una pregunta a un notebook."""

    async def _ask():
        async with await _create_client() as client:
            kwargs = {"source_ids": source_ids} if source_ids else {}
            if follow_up:
                kwargs["conversation_id"] = follow_up

            result = await client.chat.ask(notebook_id, question, **kwargs)

            # Respuesta principal
            print("RESPUESTA:")
            print(result.answer)

            # Citas
            if result.references:
                print(f"\nCITAS ({len(result.references)}):")
                for ref in result.references:
                    num = f"[{ref.citation_number}]" if ref.citation_number else ""
                    text = ref.cited_text[:150] if ref.cited_text else "(sin texto)"
                    print(f"  {num} Fuente {ref.source_id[:8]}...: {text}")

            # Metadata para follow-ups
            print(f"\n---")
            print(f"conversation_id: {result.conversation_id}")
            print(f"turn: {result.turn_number}")

            return 0

    return run_async(_ask())


def cmd_history(notebook_id: str):
    """Muestra el historial de conversaciones de un notebook."""

    async def _history():
        async with await _create_client() as client:
            history = await client.chat.get_history(notebook_id)
            print(f"HISTORIAL ({len(history)} turnos):")
            for turn in history:
                role = "Tú" if not getattr(turn, "is_follow_up", False) else "Follow-up"
                print(f"  [{role}] {str(turn)[:100]}")
            return 0

    return run_async(_history())


def cmd_configure(notebook_id: str, goal: str = None, length: str = None, prompt: str = None):
    """Configura la persona del chat."""

    async def _configure():
        from notebooklm import ChatGoal, ChatResponseLength

        goal_map = {
            "default": ChatGoal.DEFAULT,
            "learning": ChatGoal.LEARNING_GUIDE,
            "custom": ChatGoal.CUSTOM,
        }
        length_map = {
            "default": ChatResponseLength.DEFAULT,
            "longer": ChatResponseLength.LONGER,
            "shorter": ChatResponseLength.SHORTER,
        }

        async with await _create_client() as client:
            kwargs = {}
            if goal:
                kwargs["goal"] = goal_map.get(goal, ChatGoal.DEFAULT)
            if length:
                kwargs["response_length"] = length_map.get(length, ChatResponseLength.DEFAULT)
            if prompt:
                kwargs["custom_prompt"] = prompt

            result = await client.chat.configure(notebook_id, **kwargs)
            print(f"CONFIGURADO: {result}")
            return 0

    return run_async(_configure())


def main():
    parser = argparse.ArgumentParser(description="Consultas a NotebookLM")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ask = sub.add_parser("ask", help="Hacer una pregunta")
    p_ask.add_argument("--notebook-id", "--id", help="ID del notebook (o activo)")
    p_ask.add_argument("--notebook-url", help="URL del notebook")
    p_ask.add_argument("--question", "-q", required=True, help="Pregunta")
    p_ask.add_argument("--source-ids", nargs="+", help="IDs de fuentes específicas")
    p_ask.add_argument("--follow-up", help="conversation_id para follow-up")

    p_history = sub.add_parser("history", help="Ver historial de chat")
    p_history.add_argument("--notebook-id", "--id", required=True, help="ID del notebook")

    p_config = sub.add_parser("configure", help="Configurar persona del chat")
    p_config.add_argument("--notebook-id", "--id", required=True, help="ID del notebook")
    p_config.add_argument("--goal", choices=["default", "learning", "custom"])
    p_config.add_argument("--length", choices=["default", "longer", "shorter"])
    p_config.add_argument("--prompt", help="Prompt personalizado")

    args = parser.parse_args()

    # Resolver notebook ID
    from nlm_notebook import _resolve_id, _get_active_id

    if args.command == "ask":
        nid = None
        if args.notebook_url:
            nid = _resolve_id(args.notebook_url)
        elif args.notebook_id:
            nid = _resolve_id(args.notebook_id)
        else:
            nid = _get_active_id()
        if not nid:
            print("ERROR: Especifica --notebook-id, --notebook-url, o activa un notebook.")
            sys.exit(1)
        sys.exit(cmd_ask(nid, args.question, args.source_ids, args.follow_up))
    elif args.command == "history":
        sys.exit(cmd_history(_resolve_id(args.notebook_id)))
    elif args.command == "configure":
        sys.exit(cmd_configure(_resolve_id(args.notebook_id), args.goal, args.length, args.prompt))


if __name__ == "__main__":
    main()
