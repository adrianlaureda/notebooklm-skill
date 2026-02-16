# Tipos de fuente — Referencia

## Detección automática (nlm_sources.py)

El script detecta el tipo automáticamente según el input:

| Patrón | Tipo | Método API |
|--------|------|-----------|
| `youtube.com/watch?v=...` | youtube | `sources.add_youtube()` |
| `youtu.be/...` | youtube | `sources.add_youtube()` |
| `youtube.com/shorts/...` | youtube | `sources.add_youtube()` |
| `drive.google.com/...` | drive | `sources.add_drive()` |
| `docs.google.com/...` | drive | `sources.add_drive()` |
| `https://ejemplo.com/...` | url | `sources.add_url()` |
| Archivo local existente | file | `sources.add_file()` |
| Texto >200 caracteres | text | `sources.add_text()` |

## Extensiones de archivo soportadas

- Documentos: `.pdf`, `.docx`, `.txt`, `.md`
- Imágenes: `.png`, `.jpg`, `.jpeg`
- Audio: `.mp3`, `.wav`, `.m4a`
- Vídeo: `.mp4`

## Google Drive: extracción de file_id

Se extraen automáticamente de URLs como:
- `drive.google.com/file/d/{ID}/...`
- `docs.google.com/document/d/{ID}/...`
- `docs.google.com/spreadsheets/d/{ID}/...`
- `docs.google.com/presentation/d/{ID}/...`

## Límites

- **Free**: máximo 50 fuentes por notebook
- **Plus/Pro**: máximo 300 fuentes por notebook
- Archivos individuales: máximo 500.000 palabras o 200 MB

## Uso desde CLI

```bash
# Detección automática (recomendado)
python scripts/run.py nlm_sources.py add --id NOTEBOOK_ID \
  -s "https://youtube.com/watch?v=abc123" \
  -s "./apuntes.pdf" \
  -s "https://ejemplo.com/articulo"

# Forzar tipo
python scripts/run.py nlm_sources.py add --id NOTEBOOK_ID \
  -s "texto corto que parecería URL" --type text

# Debug: ver qué tipo detectaría
python scripts/run.py nlm_sources.py detect "https://youtu.be/abc"
```

## Operaciones adicionales

```bash
# Listar fuentes de un notebook
python scripts/run.py nlm_sources.py list --id NOTEBOOK_ID
```
