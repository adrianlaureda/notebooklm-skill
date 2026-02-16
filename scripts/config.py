"""
Configuración para NotebookLM Skill.
Centraliza rutas, constantes y configuración compartida.
"""

from pathlib import Path

# === Rutas principales ===
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
OUTPUTS_DIR = DATA_DIR / "outputs"
LIBRARY_FILE = DATA_DIR / "library.json"

# === notebooklm-py (nueva API) ===
NLM_HOME = Path.home() / ".notebooklm"
NLM_STORAGE_STATE = NLM_HOME / "storage_state.json"

# === Legacy (Patchright) ===
BROWSER_STATE_DIR = DATA_DIR / "browser_state"
BROWSER_PROFILE_DIR = BROWSER_STATE_DIR / "browser_profile"
STATE_FILE = BROWSER_STATE_DIR / "state.json"
AUTH_INFO_FILE = DATA_DIR / "auth_info.json"

# === Obsidian ===
VAULT_PATH = Path.home() / "Documents" / "AdrianLaureda"

# === Legacy: selectores CSS para browser automation ===
QUERY_INPUT_SELECTORS = [
    "textarea.query-box-input",
    'textarea[aria-label="Feld für Anfragen"]',
    'textarea[aria-label="Input for queries"]',
]

RESPONSE_SELECTORS = [
    ".to-user-container .message-text-content",
    "[data-message-author='bot']",
    "[data-message-author='assistant']",
]

# === Legacy: configuración de browser ===
BROWSER_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--no-first-run',
    '--no-default-browser-check'
]

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# === Timeouts ===
LOGIN_TIMEOUT_MINUTES = 10
QUERY_TIMEOUT_SECONDS = 120
PAGE_LOAD_TIMEOUT = 30000
STUDIO_TIMEOUT_SECONDS = 300
STUDIO_POLL_INTERVAL = 5
