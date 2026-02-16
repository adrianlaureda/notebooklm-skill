---
name: notebooklm
description: >
  Automatiza NotebookLM: crea cuadernos, añade fuentes (URLs, YouTube, PDFs,
  imágenes, audio, texto, Google Drive), queries con citas, Studio completo
  (podcasts, vídeos, quizzes, flashcards, presentaciones, informes, mapas mentales),
  descarga outputs, guarda análisis en Obsidian.
---

# NotebookLM — Skill de automatización

Usa **notebooklm-py** (API Python, sin browser automation) para automatizar NotebookLM.
Todos los scripts `nlm_*` se ejecutan vía `run.py` que gestiona el venv automáticamente.

## Workflow (Decision Tree)

### Crear notebook con fuentes
1. Verificar auth → `python scripts/run.py nlm_auth.py check`
2. Crear notebook → `python scripts/run.py nlm_notebook.py create --name "Tema"`
3. Añadir fuentes → `python scripts/run.py nlm_sources.py add --id NOTEBOOK_ID -s URL -s archivo.pdf`
4. Verificar → consultar checklist abajo

### Consultar notebook existente
1. `python scripts/run.py nlm_auth.py check`
2. `python scripts/run.py nlm_query.py ask --id NOTEBOOK_ID -q "Tu pregunta"`
3. Para follow-up: usar `--follow-up CONVERSATION_ID` del resultado anterior

### Generar contenido Studio
1. `python scripts/run.py nlm_studio.py generate --id NOTEBOOK_ID -t audio`
2. Tipos: `audio`, `video`, `quiz`, `flashcards`, `report`, `slide_deck`, `infographic`, `data_table`, `mind_map`
3. Opciones por tipo → consultar `references/studio-generation.md`

### Pipeline completo (fuentes → análisis → outputs)
```bash
python scripts/run.py nlm_workflow.py \
  --name "Mi tema" \
  -s "https://url1.com" -s "archivo.pdf" \
  -q "Pregunta 1" -q "Pregunta 2" \
  -t audio -t quiz \
  --obsidian "NotebookLM/mi-tema.md"
```
→ Detalle en `references/pipeline-workflow.md`

### Problemas de autenticación
→ Consultar `references/auth-migration.md`

## Reglas core

- **Always** usar `python scripts/run.py nlm_*.py`, NUNCA scripts directamente
- **Always** verificar auth antes de cualquier operación (`nlm_auth.py check`)
- **Always** detectar tipo de fuente automáticamente (no pedir al usuario)
- **Always** usar `--language es` para contenido Studio en español
- **Never** mezclar scripts `nlm_*` con scripts legacy en la misma operación
- **Consider** YouTube MCP para descubrir vídeos antes de añadirlos como fuentes

## Detección automática de fuentes

| Input | Tipo detectado |
|-------|---------------|
| `youtube.com/watch?...`, `youtu.be/...` | youtube |
| `drive.google.com/...`, `docs.google.com/...` | drive |
| `https://ejemplo.com/...` | url |
| `./doc.pdf`, `~/foto.png`, `audio.mp3` | file |
| Texto largo (>200 chars) | text |

Extensiones soportadas: `.pdf`, `.docx`, `.txt`, `.md`, `.png`, `.jpg`, `.jpeg`, `.mp3`, `.wav`, `.m4a`, `.mp4`

## Quick Reference

| Propiedad | Valor |
|-----------|-------|
| Lib | notebooklm-py (PyPI) |
| Auth | `~/.notebooklm/storage_state.json` |
| Library | `data/library.json` |
| Outputs | `data/outputs/` |
| Max fuentes/notebook | 50 (free) / 300 (pro) |
| API | async (wrapper síncrono en nlm_client.py) |

## Script Reference

| Script | Función |
|--------|---------|
| `nlm_auth.py` | check, setup, migrate, validate |
| `nlm_notebook.py` | create, list, delete, get, activate, sync |
| `nlm_sources.py` | add, list, detect |
| `nlm_query.py` | ask, history, configure |
| `nlm_studio.py` | generate, list |
| `nlm_workflow.py` | Pipeline completo end-to-end |
| `nlm_obsidian.py` | Guardar resultados en vault |

## Checklist

- [ ] Auth válida (`nlm_auth.py check` → OK)
- [ ] Fuentes añadidas sin error
- [ ] Query devuelve respuesta con citas
- [ ] Studio genera y descarga correctamente
- [ ] Library.json actualizado

## Legacy (deprecated)

Scripts `ask_question.py`, `auth_manager.py`, `notebook_manager.py`, `studio_generator.py`
siguen funcionando pero usan Patchright (browser automation). Usar `nlm_*` en su lugar.
