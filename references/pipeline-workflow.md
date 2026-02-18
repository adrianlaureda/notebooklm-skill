# Pipeline Workflow — Referencia

## Flujo completo

```
1. VERIFICAR AUTH → nlm_auth.py check
2. CREAR NOTEBOOK → nlm_notebook.py create --name "..."
3. AÑADIR FUENTES → nlm_sources.py add (detección auto, batch)
4. QUERIES (opcional) → nlm_query.py ask -q "..."
5. STUDIO (opcional) → nlm_studio.py generate -t tipo
6. OBSIDIAN (opcional) → nlm_obsidian.py (nota con resumen + links)
```

## Comando unificado (nlm_workflow.py)

```bash
python scripts/run.py nlm_workflow.py \
  --name "Sintaxis 4ESO" \
  -s "https://ejemplo.com/sintaxis" \
  -s "./apuntes_sintaxis.pdf" \
  -s "https://youtube.com/watch?v=abc123" \
  -q "¿Qué es el complemento directo?" \
  -q "¿Cuáles son los tipos de oraciones compuestas?" \
  -t audio -t quiz -t report \
  --obsidian "NotebookLM/Sintaxis 4ESO.md" \
  -l es
```

## Caso: analizar canal de YouTube

1. Usar YouTube MCP para descubrir vídeos relevantes:
   - `youtube_search` o `youtube_get_channel` para obtener URLs
2. Pasarlas como fuentes al pipeline:
   ```bash
   python scripts/run.py nlm_workflow.py \
     --name "Canal educativo" \
     -s "https://youtube.com/watch?v=video1" \
     -s "https://youtube.com/watch?v=video2" \
     -s "https://youtube.com/watch?v=video3" \
     -q "Resume los temas principales" \
     -t audio
   ```

## Caso: material educativo desde Google Drive

1. Buscar documentos con gogcli: `gog --account trabajo drive search "tema" --json`
2. Obtener URLs: `gog --account trabajo drive url <fileId>`
3. Pasarlas como fuentes tipo `drive`

## Paso a paso manual (sin workflow)

```bash
# 1. Auth
python scripts/run.py nlm_auth.py check

# 2. Crear
python scripts/run.py nlm_notebook.py create --name "Mi tema"
# → Anota el ID

# 3. Fuentes
python scripts/run.py nlm_sources.py add --id ID \
  -s "https://url1.com" -s "https://url2.com"

# 4. Query
python scripts/run.py nlm_query.py ask --id ID -q "Pregunta"

# 5. Studio
python scripts/run.py nlm_studio.py generate --id ID -t quiz -l es

# 6. Obsidian
python scripts/run.py nlm_obsidian.py \
  --notebook-id ID --notebook-name "Mi tema" \
  --output "NotebookLM/mi-tema.md"
```

## Nota sobre Obsidian

La nota generada incluye:
- Frontmatter con `source: notebooklm`, ID, nombre, fecha, URL
- Sección de preguntas y respuestas
- Lista de archivos generados (con wikilinks)
- Enlace directo al notebook en NotebookLM
