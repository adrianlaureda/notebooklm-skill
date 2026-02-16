# Auth Migration — Referencia

## Estado actual

El skill tiene dos sistemas de auth:
- **Nuevo** (notebooklm-py): `~/.notebooklm/storage_state.json`
- **Legacy** (Patchright): `data/browser_state/state.json`

Ambos usan el mismo formato Playwright `storage_state` JSON → la migración es copia directa.

## Migración automática

```bash
python scripts/run.py nlm_auth.py migrate
```

Esto:
1. Busca `~/.notebooklm/storage_state.json` (si ya existe, no hace nada)
2. Copia `data/browser_state/state.json` → `~/.notebooklm/storage_state.json`
3. Valida con una llamada real a la API

Usa `--force` para sobreescribir auth existente.

## Login nuevo (sin auth previa)

```bash
python scripts/run.py nlm_auth.py setup
```

Ejecuta `notebooklm login` que:
1. Abre Chromium
2. Navega a NotebookLM
3. Espera a que el usuario inicie sesión con Google
4. Guarda cookies en `~/.notebooklm/storage_state.json`

## Verificación

```bash
# Solo comprueba que el archivo existe y tiene cookies válidas
python scripts/run.py nlm_auth.py check

# Hace una llamada real a la API (lista notebooks)
python scripts/run.py nlm_auth.py validate
```

## Troubleshooting

### Cookies expiradas
- Síntoma: `validate` falla con error de auth
- Solución: `python scripts/run.py nlm_auth.py setup` (re-login)

### Múltiples cuentas Google
- Usar `NOTEBOOKLM_HOME` para separar almacenes:
  ```bash
  NOTEBOOKLM_HOME=~/.notebooklm-trabajo python scripts/run.py nlm_auth.py setup
  ```

### notebooklm command not found
- Asegurarse de que el paquete está instalado en el venv:
  ```bash
  pip install "notebooklm-py[browser]"
  playwright install chromium
  ```
- O ejecutar desde el venv del skill:
  ```bash
  .venv/bin/notebooklm login
  ```

### Auth legacy sigue funcionando
- Los scripts legacy (`ask_question.py`, etc.) siguen usando `data/browser_state/`
- No se eliminan. Ambos sistemas coexisten
- Para nuevas operaciones, siempre usar scripts `nlm_*`

## Precedencia de auth (notebooklm-py)

1. Argumento explícito `path` en `from_storage()`
2. Variable de entorno `NOTEBOOKLM_AUTH_JSON`
3. `$NOTEBOOKLM_HOME/storage_state.json`
4. `~/.notebooklm/storage_state.json`
