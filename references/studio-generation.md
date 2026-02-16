# Studio Generation — Referencia

## Tipos disponibles

| Tipo | Descarga | Opciones principales |
|------|----------|---------------------|
| `audio` | `.mp3` | format, length |
| `video` | `.mp4` | format, style |
| `quiz` | `.json`/`.md`/`.html` | difficulty, quantity |
| `flashcards` | `.json`/`.md`/`.html` | difficulty, quantity |
| `report` | `.md` | format, title, description |
| `slide_deck` | `.pdf` | format, length |
| `infographic` | `.png` | orientation, detail |
| `data_table` | `.csv` | description |
| `mind_map` | `.json` | (sin opciones extra) |

## Opciones por tipo

### Audio
- `--format`: `deep_dive` (default), `brief`, `critique`, `debate`
- `--length`: `short`, `default`, `long`

### Video
- `--format`: `explainer` (default), `brief`
- `--style`: `auto`, `classic`, `whiteboard`, `kawaii`, `anime`, `watercolor`

### Quiz / Flashcards
- `--difficulty`: `easy`, `medium` (default), `hard`
- `--quantity`: `fewer`, `standard` (default)
- `--output-format`: `json` (default), `markdown`, `html`

### Report
- `--format`: `briefing`, `study_guide` (default), `blog`, `custom`
- `--title`: título del informe
- `--description`: descripción del contenido

### Slide Deck
- `--format`: `detailed_deck` (default), `presenter_slides`
- `--length`: `default`, `short`

### Infographic
- Orientación y detalle configurables (se exponen en futuras versiones)

### Data Table
- `--description`: descripción de qué datos extraer

## Ejemplos de uso

```bash
# Podcast educativo en español
python scripts/run.py nlm_studio.py generate --id ID -t audio \
  --format deep_dive --length default -l es \
  -i "Podcast para alumnos de 15 años, tono cercano"

# Quiz de dificultad media en markdown
python scripts/run.py nlm_studio.py generate --id ID -t quiz \
  --difficulty medium --output-format markdown -l es

# Guía de estudio
python scripts/run.py nlm_studio.py generate --id ID -t report \
  --format study_guide --title "Guía de sintaxis" -l es

# Vídeo estilo pizarra
python scripts/run.py nlm_studio.py generate --id ID -t video \
  --format explainer --style whiteboard -l es

# Listar artefactos generados
python scripts/run.py nlm_studio.py list --id ID
python scripts/run.py nlm_studio.py list --id ID -t quiz
```

## Timeouts

- Audio/Video: hasta 5 min (timeout default: 300s)
- Quiz/Flashcards/Report: ~30s-2min
- Mind map: síncrono (inmediato)
- Poll interval: 5s (configurable con `--poll-interval`)
