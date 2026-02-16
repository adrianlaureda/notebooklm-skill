#!/usr/bin/env python3
"""
[DEPRECATED] Usar nlm_studio.py en su lugar.
Genera contenido del Studio de NotebookLM (vídeos, presentaciones, etc.)
Modo interactivo: detecta y permite configurar las opciones reales de la UI.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR, BROWSER_STATE_DIR

# Tipos de contenido soportados
CONTENT_TYPES = {
    "video": {
        "name": "Resumen de vídeo",
        "button_text": "Resumen de vídeo",
        "icon": "🎬"
    },
    "audio": {
        "name": "Resumen de audio",
        "button_text": "Resumen de audio",
        "icon": "🎧"
    },
    "mindmap": {
        "name": "Mapa mental",
        "button_text": "Mapa mental",
        "icon": "🧠"
    },
    "quiz": {
        "name": "Cuestionario",
        "button_text": "Cuestionario",
        "icon": "❓"
    },
    "infographic": {
        "name": "Infografía",
        "button_text": "Infografía",
        "icon": "📊"
    },
    "presentation": {
        "name": "Presentación",
        "button_text": "Presentación",
        "icon": "📽️"
    },
    "table": {
        "name": "Tabla de datos",
        "button_text": "Tabla de datos",
        "icon": "📋"
    }
}


def get_notebook_url(notebook_id: str) -> str:
    """Construye la URL del cuaderno."""
    return f"https://notebooklm.google.com/notebook/{notebook_id}"


def detectar_opciones_ui(page) -> dict:
    """
    Detecta las opciones disponibles en el diálogo de NotebookLM Studio.
    Estructura del diálogo:
    - Formato: tarjetas clickeables (Información detallada, Breve, Crítica, Debate)
    - Idioma: dropdown selector
    - Duración: opciones Corto / Predeterminada
    - Prompt: textarea para instrucciones personalizadas

    Returns:
        Dict con las opciones detectadas
    """
    opciones = {
        "formato": [],      # Tarjetas de formato (cards)
        "estilo": [],       # Estilos visuales (solo para vídeo)
        "idioma": None,     # Dropdown de idioma
        "duracion": [],     # Opciones de duración (solo para audio)
        "prompt": None      # Campo de texto para instrucciones
    }

    # Buscar el diálogo de personalización
    dialog = page.query_selector('[role="dialog"], [class*="modal"], [class*="dialog"], [class*="customize"]')
    container = dialog if dialog else page

    # 1. Detectar tarjetas de FORMATO
    # Son elementos clickeables con títulos como "Información detallada", "Breve", etc.
    try:
        # Buscar por texto conocido de las opciones de formato (sin duplicados)
        # Audio: Información detallada, Breve, Crítica, Debate
        # Video: Video explicativo, Breve
        formato_textos = ["Video explicativo", "Información detallada", "Breve", "Crítica", "Debate"]
        formatos_encontrados = set()  # Evitar duplicados

        for texto in formato_textos:
            if texto in formatos_encontrados:
                continue

            # Buscar elemento que contenga exactamente este texto
            card = container.query_selector(f'//*[text()="{texto}"]')
            if not card:
                # Fallback: buscar con contains
                card = container.query_selector(f'//*[contains(text(), "{texto}")]')

            if card:
                formatos_encontrados.add(texto)

                # Verificar si está seleccionado (buscar clase selected, active, checked)
                is_selected = card.evaluate("""el => {
                    let current = el;
                    for (let i = 0; i < 5; i++) {
                        const classes = current.className || '';
                        const attr = current.getAttribute('aria-selected') || current.getAttribute('aria-checked');
                        if (classes.includes('selected') || classes.includes('active') ||
                            classes.includes('checked') || attr === 'true') {
                            return true;
                        }
                        current = current.parentElement;
                        if (!current) break;
                    }
                    return false;
                }""")

                # Obtener descripción del siguiente sibling o del contenedor padre
                descripcion = card.evaluate("""el => {
                    // Intentar obtener el siguiente elemento hermano con descripción
                    let sibling = el.nextElementSibling;
                    if (sibling && sibling.textContent) {
                        return sibling.textContent.trim().substring(0, 60);
                    }
                    // Si no, buscar en el contenedor padre
                    const parent = el.parentElement;
                    if (parent) {
                        // Buscar elementos que parezcan descripciones (no el título)
                        const children = parent.querySelectorAll('*');
                        for (const child of children) {
                            if (child !== el && child.textContent.length > 20 && child.textContent.length < 200) {
                                return child.textContent.trim().substring(0, 60);
                            }
                        }
                    }
                    return '';
                }""")

                opciones["formato"].append({
                    "element": card,
                    "label": texto,
                    "descripcion": descripcion,
                    "selected": is_selected
                })
    except Exception as e:
        print(f"  ⚠️ Error detectando formato: {e}")

    # 2. Detectar DROPDOWN de idioma
    try:
        # Buscar por label "Seleccionar idioma" o select/dropdown cercano
        idioma_label = container.query_selector('//*[contains(text(), "idioma") or contains(text(), "Idioma") or contains(text(), "language")]')
        if idioma_label:
            # Buscar select, dropdown o botón cercano
            select = container.query_selector('select, [role="listbox"], [role="combobox"]')
            if not select:
                # Buscar botón con dropdown (Material design usa esto)
                select = idioma_label.evaluate("""el => {
                    const parent = el.parentElement;
                    if (parent) {
                        const btn = parent.querySelector('button, [role="button"]');
                        return btn ? true : false;
                    }
                    return false;
                }""")
                if select:
                    select = container.query_selector('button:has-text("español"), button:has-text("english")')

            if select:
                valor_actual = select.evaluate("el => el.value || el.textContent || ''")
                opciones["idioma"] = {
                    "element": select,
                    "valor": valor_actual.strip()[:30]
                }
    except Exception as e:
        print(f"  ⚠️ Error detectando idioma: {e}")

    # 3. Detectar opciones de DURACIÓN (solo para audio)
    try:
        duracion_textos = ["Corto", "Predeterminada", "Predeterminado", "Largo",
                          "Short", "Default", "Long"]

        for texto in duracion_textos:
            # Buscar checkbox, radio o botón con este texto
            elemento = container.query_selector(f'//*[contains(text(), "{texto}")]')
            if elemento:
                # Verificar si es clickeable o tiene checkbox asociado
                is_checked = elemento.evaluate("""el => {
                    // Buscar checkbox cercano
                    const parent = el.closest('label') || el.parentElement;
                    if (parent) {
                        const checkbox = parent.querySelector('input[type="checkbox"], input[type="radio"]');
                        if (checkbox) return checkbox.checked;
                    }
                    // Verificar clases de selección
                    const classes = el.className || '';
                    return classes.includes('selected') || classes.includes('active') || classes.includes('checked');
                }""")

                opciones["duracion"].append({
                    "element": elemento,
                    "label": texto,
                    "checked": is_checked
                })
    except Exception as e:
        print(f"  ⚠️ Error detectando duración: {e}")

    # 4. Detectar ESTILOS VISUALES (solo para vídeo)
    try:
        # Buscar sección "Elige un estilo visual"
        estilo_label = container.query_selector('//*[contains(text(), "estilo visual") or contains(text(), "Estilo visual") or contains(text(), "visual style")]')
        if estilo_label:
            # Los estilos son tarjetas con imágenes
            estilo_textos = ["Selección automática", "Personalizado", "Clásico", "Pizarra",
                           "Kawaii", "Anime", "Retro", "Minimalista", "Acuarela"]
            estilos_encontrados = set()

            for texto in estilo_textos:
                if texto in estilos_encontrados:
                    continue

                elemento = container.query_selector(f'//*[text()="{texto}"]')
                if not elemento:
                    elemento = container.query_selector(f'//*[contains(text(), "{texto}")]')

                if elemento:
                    estilos_encontrados.add(texto)

                    # Verificar si está seleccionado
                    is_selected = elemento.evaluate("""el => {
                        let current = el;
                        for (let i = 0; i < 5; i++) {
                            const classes = current.className || '';
                            const attr = current.getAttribute('aria-selected') || current.getAttribute('aria-checked');
                            if (classes.includes('selected') || classes.includes('active') ||
                                classes.includes('checked') || attr === 'true') {
                                return true;
                            }
                            // Buscar checkmark/tick dentro del contenedor
                            const checkmark = current.querySelector('svg, [class*="check"], [class*="tick"]');
                            if (checkmark) return true;
                            current = current.parentElement;
                            if (!current) break;
                        }
                        return false;
                    }""")

                    opciones["estilo"].append({
                        "element": elemento,
                        "label": texto,
                        "selected": is_selected
                    })
    except Exception as e:
        print(f"  ⚠️ Error detectando estilos: {e}")

    # 5. Detectar TEXTAREA de instrucciones/prompt
    try:
        textarea = container.query_selector('textarea')
        if textarea:
            placeholder = textarea.get_attribute("placeholder") or ""
            valor = textarea.evaluate("el => el.value || ''")
            opciones["prompt"] = {
                "element": textarea,
                "placeholder": placeholder,
                "valor": valor
            }
    except Exception as e:
        print(f"  ⚠️ Error detectando prompt: {e}")

    return opciones


def mostrar_opciones_detectadas(opciones: dict) -> None:
    """Muestra las opciones detectadas de forma legible."""
    print(f"\n{'─'*60}")
    print("📋 OPCIONES DISPONIBLES")
    print('─'*60)

    tiene_opciones = False

    # Formato (tarjetas)
    if opciones.get("formato"):
        tiene_opciones = True
        print(f"\n🎨 Formato ({len(opciones['formato'])} opciones):")
        for i, f in enumerate(opciones["formato"]):
            marca = "▶" if f.get("selected") else "○"
            desc = f" - {f['descripcion'][:40]}..." if f.get('descripcion') else ""
            print(f"   {marca} [{i+1}] {f['label']}{desc}")

    # Estilos visuales (solo vídeo)
    if opciones.get("estilo"):
        tiene_opciones = True
        print(f"\n🎭 Estilo visual ({len(opciones['estilo'])} opciones):")
        for i, e in enumerate(opciones["estilo"]):
            marca = "▶" if e.get("selected") else "○"
            print(f"   {marca} [{i+1}] {e['label']}")

    # Idioma (dropdown)
    if opciones.get("idioma"):
        tiene_opciones = True
        valor = opciones["idioma"].get("valor", "No detectado")
        print(f"\n🌐 Idioma: {valor}")

    # Duración (solo audio)
    if opciones.get("duracion"):
        tiene_opciones = True
        print(f"\n⏱️ Duración:")
        for i, d in enumerate(opciones["duracion"]):
            marca = "☑" if d.get("checked") else "☐"
            print(f"   {marca} [{i+1}] {d['label']}")

    # Campo de prompt
    if opciones.get("prompt"):
        tiene_opciones = True
        placeholder = opciones["prompt"].get("placeholder", "Instrucciones personalizadas")
        print(f"\n✏️ Instrucciones personalizadas:")
        if len(placeholder) > 50:
            print(f"   Placeholder: \"{placeholder[:50]}...\"")
        else:
            print(f"   Placeholder: \"{placeholder}\"")

    if not tiene_opciones:
        print("\n   ℹ️ No se detectaron opciones configurables")
        print("   Es posible que el diálogo no se haya abierto correctamente")

    print('─'*60)


def configurar_opciones_interactivo(page, opciones: dict) -> dict:
    """
    Permite al usuario configurar las opciones de forma interactiva.

    Returns:
        Dict con las configuraciones aplicadas
    """
    config_aplicada = {
        "formato": None,
        "estilo": None,
        "idioma": None,
        "duracion": None,
        "prompt": None
    }

    # 1. Configurar FORMATO
    if opciones.get("formato"):
        print(f"\n🎨 Selecciona formato:")
        for i, f in enumerate(opciones["formato"]):
            marca = "▶" if f.get("selected") else "○"
            print(f"   {marca} [{i+1}] {f['label']}")

        try:
            sel = input(f"\n   Formato [Enter = usar actual]: ").strip()
            if sel and sel.isdigit():
                idx = int(sel) - 1
                if 0 <= idx < len(opciones["formato"]):
                    # Click en el elemento padre clickeable
                    elemento = opciones["formato"][idx]["element"]
                    elemento.evaluate("""el => {
                        // Buscar el contenedor clickeable y hacer click
                        let current = el;
                        for (let i = 0; i < 5; i++) {
                            if (current.onclick || current.getAttribute('tabindex') !== null) {
                                current.click();
                                return;
                            }
                            current = current.parentElement;
                            if (!current) break;
                        }
                        // Fallback: click en el elemento original
                        el.click();
                    }""")
                    config_aplicada["formato"] = opciones["formato"][idx]["label"]
                    print(f"   ✅ Formato: {opciones['formato'][idx]['label']}")
                    time.sleep(0.5)
        except Exception as e:
            print(f"   ⚠️ Error seleccionando formato: {e}")

    # 2. Configurar ESTILO VISUAL (solo para vídeo)
    if opciones.get("estilo"):
        print(f"\n🎭 Selecciona estilo visual:")
        for i, e in enumerate(opciones["estilo"]):
            marca = "▶" if e.get("selected") else "○"
            print(f"   {marca} [{i+1}] {e['label']}")

        try:
            sel = input(f"\n   Estilo [Enter = usar actual]: ").strip()
            if sel and sel.isdigit():
                idx = int(sel) - 1
                if 0 <= idx < len(opciones["estilo"]):
                    elemento = opciones["estilo"][idx]["element"]
                    elemento.evaluate("""el => {
                        let current = el;
                        for (let i = 0; i < 5; i++) {
                            if (current.onclick || current.getAttribute('tabindex') !== null) {
                                current.click();
                                return;
                            }
                            current = current.parentElement;
                            if (!current) break;
                        }
                        el.click();
                    }""")
                    config_aplicada["estilo"] = opciones["estilo"][idx]["label"]
                    print(f"   ✅ Estilo: {opciones['estilo'][idx]['label']}")
                    time.sleep(0.5)
        except Exception as e:
            print(f"   ⚠️ Error seleccionando estilo: {e}")

    # 3. Configurar DURACIÓN
    if opciones.get("duracion"):
        print(f"\n⏱️ Selecciona duración:")
        for i, d in enumerate(opciones["duracion"]):
            marca = "☑" if d.get("checked") else "☐"
            print(f"   {marca} [{i+1}] {d['label']}")

        try:
            sel = input(f"\n   Duración [Enter = usar actual]: ").strip()
            if sel and sel.isdigit():
                idx = int(sel) - 1
                if 0 <= idx < len(opciones["duracion"]):
                    elemento = opciones["duracion"][idx]["element"]
                    # Click en el label o checkbox asociado
                    elemento.evaluate("""el => {
                        const parent = el.closest('label') || el.parentElement;
                        if (parent) {
                            const checkbox = parent.querySelector('input[type="checkbox"], input[type="radio"]');
                            if (checkbox) {
                                checkbox.click();
                                return;
                            }
                        }
                        el.click();
                    }""")
                    config_aplicada["duracion"] = opciones["duracion"][idx]["label"]
                    print(f"   ✅ Duración: {opciones['duracion'][idx]['label']}")
                    time.sleep(0.3)
        except Exception as e:
            print(f"   ⚠️ Error seleccionando duración: {e}")

    # 3. Configurar PROMPT/instrucciones
    if opciones.get("prompt"):
        placeholder = opciones["prompt"].get("placeholder", "Instrucciones")
        print(f"\n✏️ Instrucciones personalizadas")
        if len(placeholder) > 50:
            print(f"   (Sugerencias: {placeholder[:50]}...)")
        else:
            print(f"   (Sugerencias: {placeholder})")

        try:
            texto = input("   Tu prompt [Enter para omitir]: ").strip()
            if texto:
                opciones["prompt"]["element"].fill(texto)
                config_aplicada["prompt"] = texto
                print(f"   ✅ Prompt aplicado")
                time.sleep(0.3)
        except Exception as e:
            print(f"   ⚠️ Error aplicando prompt: {e}")

    return config_aplicada


def generate_content(notebook_id: str, content_type: str,
                     headless: bool = False, interactive: bool = True,
                     auto_generate: bool = False, explore_only: bool = False):
    """
    Genera contenido del Studio de NotebookLM.

    Args:
        notebook_id: ID del cuaderno
        content_type: Tipo de contenido (video, audio, mindmap, etc.)
        headless: Si True, ejecuta sin ventana visible
        interactive: Si True, permite configurar opciones interactivamente
        auto_generate: Si True, genera automáticamente sin confirmación
        explore_only: Si True, solo detecta opciones sin generar

    Returns:
        Dict con el resultado de la generación
    """
    from patchright.sync_api import sync_playwright

    if content_type not in CONTENT_TYPES:
        return {"status": "error", "message": f"Tipo no soportado: {content_type}"}

    content_info = CONTENT_TYPES[content_type]
    state_file = BROWSER_STATE_DIR / "state.json"
    profile_dir = BROWSER_STATE_DIR / "browser_profile"

    if not state_file.exists():
        return {"status": "error", "message": "No hay sesión autenticada"}

    print(f"\n{'='*60}")
    print(f"{content_info['icon']} {content_info['name'].upper()}")
    print('='*60)

    result = {
        "status": "pending",
        "type": content_type,
        "notebook_id": notebook_id,
        "started_at": datetime.now().isoformat()
    }

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # Cargar cookies
        with open(state_file, 'r') as f:
            state = json.load(f)
            context.add_cookies(state.get('cookies', []))

        page = context.new_page()

        try:
            # 1. Navegar al cuaderno
            notebook_url = get_notebook_url(notebook_id)
            print(f"\n🌐 Navegando a {notebook_url}...")
            page.goto(notebook_url, wait_until="domcontentloaded", timeout=45000)

            # Verificar sesión
            if "accounts.google.com" in page.url:
                return {"status": "error", "message": "Sesión expirada"}

            print("⏳ Esperando carga completa...")
            time.sleep(3)

            # Guardar screenshot del estado inicial
            initial_screenshot = DATA_DIR / f"studio_initial_{content_type}.png"
            page.screenshot(path=str(initial_screenshot))
            result["initial_screenshot"] = str(initial_screenshot)
            print(f"📸 Estado inicial guardado: {initial_screenshot}")

            # 2. Buscar el icono de edición (lápiz) junto al tipo de contenido EXACTO
            button_text = content_info["button_text"]
            print(f"🔍 Buscando opciones de '{button_text}'...")

            # Estrategia: Buscar el texto EXACTO primero, luego el icono de edición cercano
            # Esto evita confundir "Resumen de vídeo" con "Resumen de audio"
            edit_button_found = False

            try:
                # Método 1: Buscar el texto exacto y luego el botón de edición en su contenedor
                # Usar JavaScript para búsqueda precisa
                edit_button_found = page.evaluate(f'''() => {{
                    // Buscar todos los elementos que contengan el texto exacto
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );

                    let node;
                    while (node = walker.nextNode()) {{
                        // Buscar coincidencia exacta o muy cercana
                        const text = node.textContent.trim();
                        if (text === "{button_text}" || text.startsWith("{button_text}")) {{
                            // Encontrado! Buscar el contenedor padre
                            let container = node.parentElement;
                            for (let i = 0; i < 5; i++) {{
                                if (!container) break;

                                // Buscar botón de edición en este contenedor
                                const editBtn = container.querySelector(
                                    'button[aria-label*="edit"], button[aria-label*="Editar"], ' +
                                    'button[aria-label*="personalizar"], button[aria-label*="Personalizar"], ' +
                                    'button span.material-icons, [data-icon="edit"]'
                                );

                                if (editBtn) {{
                                    // Verificar que es un botón de edición (icono de lápiz)
                                    const btn = editBtn.closest('button') || editBtn;
                                    btn.click();
                                    return true;
                                }}

                                container = container.parentElement;
                            }}
                        }}
                    }}
                    return false;
                }}''')

                if edit_button_found:
                    print(f"✅ Abriendo configuración (coincidencia exacta)...")

            except Exception as e:
                print(f"  ⚠️ Búsqueda exacta falló: {e}")

            # Método 2: Fallback con selectores de Playwright más específicos
            if not edit_button_found:
                # Usar :text-is() para coincidencia exacta en lugar de :text() o has-text
                edit_selectors = [
                    # Coincidencia exacta con :text-is()
                    f':text-is("{button_text}") >> xpath=ancestor::*[position() <= 3]//button',
                    # XPath con texto exacto
                    f'xpath=//*[normalize-space(text())="{button_text}"]/ancestor::*[position() <= 3]//button',
                    # Buscar por aria-label exacto
                    f'button[aria-label="{button_text}"]',
                    f'button[aria-label="Editar {button_text}"]',
                    f'button[aria-label="Personalizar {button_text}"]',
                ]

                for selector in edit_selectors:
                    try:
                        if 'xpath=' in selector:
                            locator = page.locator(selector).first
                        else:
                            locator = page.locator(selector).first

                        if locator.count() > 0:
                            locator.click()
                            edit_button_found = True
                            print(f"✅ Abriendo configuración (selector específico)...")
                            break
                    except:
                        continue

            # Método 3: Si aún no encontramos, intentar clic directo en el elemento con texto exacto
            if not edit_button_found:
                print("  ℹ️ No se encontró icono de edición, intentando clic directo...")
                button_selectors = [
                    f':text-is("{button_text}")',
                    f'text="{button_text}"',
                    f'[aria-label="{button_text}"]',
                ]

                button_found = False
                for selector in button_selectors:
                    try:
                        button = page.wait_for_selector(selector, timeout=3000)
                        if button:
                            button.click()
                            button_found = True
                            print(f"✅ Clic en '{button_text}'")
                            break
                    except:
                        continue

                if not button_found:
                    screenshot_path = DATA_DIR / f"debug_studio_{content_type}.png"
                    page.screenshot(path=str(screenshot_path))
                    return {
                        "status": "error",
                        "message": f"No se encontró el botón '{button_text}'",
                        "debug_screenshot": str(screenshot_path)
                    }

            # 3. Esperar a que aparezca el diálogo
            print("⏳ Esperando diálogo de configuración...")
            time.sleep(3)

            # 4. Detectar opciones disponibles en la UI
            print("🔎 Detectando opciones de la interfaz...")
            opciones = detectar_opciones_ui(page)

            # Guardar screenshot del diálogo
            dialog_screenshot = DATA_DIR / f"studio_dialog_{content_type}.png"
            page.screenshot(path=str(dialog_screenshot))
            result["dialog_screenshot"] = str(dialog_screenshot)

            # 5. Mostrar opciones detectadas
            mostrar_opciones_detectadas(opciones)

            # 6. En modo exploración, salir aquí sin generar
            if explore_only:
                result["status"] = "explored"
                result["opciones_detectadas"] = {
                    "formato": [f["label"] for f in opciones.get("formato", [])],
                    "idioma": opciones.get("idioma", {}).get("valor") if opciones.get("idioma") else None,
                    "duracion": [d["label"] for d in opciones.get("duracion", [])],
                    "tiene_prompt": opciones.get("prompt") is not None
                }
                print("\n✅ Exploración completada (no se generó contenido)")
                return result

            # 7. Modo interactivo: configurar opciones
            if interactive:
                print("\n💡 Configura las opciones o presiona Enter para usar valores por defecto")
                config = configurar_opciones_interactivo(page, opciones)
                result["config_aplicada"] = config

                # Esperar un momento para que la UI se actualice
                time.sleep(1)

                # Tomar screenshot después de configurar
                config_screenshot = DATA_DIR / f"studio_config_{content_type}.png"
                page.screenshot(path=str(config_screenshot))
                result["config_screenshot"] = str(config_screenshot)

            # 8. Confirmar antes de generar
            if not auto_generate:
                print(f"\n{'─'*60}")
                confirmar = input("¿Iniciar generación? [S/n]: ").strip().lower()
                if confirmar in ("n", "no"):
                    print("\n❌ Generación cancelada")
                    result["status"] = "cancelled"
                    return result

            # 8. Buscar y hacer clic en el botón de generar
            print("\n🚀 Iniciando generación...")
            generate_selectors = [
                'button:has-text("Generar")',
                'button:has-text("Crear")',
                'button:has-text("Generate")',
                'button:has-text("Create")',
                'button[type="submit"]'
            ]

            gen_clicked = False
            for selector in generate_selectors:
                try:
                    gen_button = page.wait_for_selector(selector, timeout=3000)
                    if gen_button:
                        gen_button.click()
                        gen_clicked = True
                        print("✅ Generación iniciada")
                        break
                except:
                    continue

            if not gen_clicked:
                print("⚠️ No se encontró botón de generar - puede que ya haya iniciado")

            # 9. Esperar generación
            print("⏳ Esperando generación (puede tardar varios minutos)...")

            max_wait = 300  # 5 minutos máximo
            start_time = time.time()

            while time.time() - start_time < max_wait:
                try:
                    success_indicators = [
                        'text="completado"',
                        'text="listo"',
                        'text="Ver"',
                        'text="Descargar"',
                        '[class*="success"]',
                        '[class*="complete"]'
                    ]

                    for indicator in success_indicators:
                        try:
                            element = page.query_selector(indicator)
                            if element:
                                print("✅ Generación completada")
                                result["status"] = "ok"
                                result["completed_at"] = datetime.now().isoformat()
                                break
                        except:
                            continue

                    if result["status"] == "ok":
                        break

                except:
                    pass

                time.sleep(5)
                elapsed = int(time.time() - start_time)
                print(f"⏳ Esperando... ({elapsed}s)")

            # 10. Capturar resultado final
            screenshot_path = DATA_DIR / f"studio_{content_type}_{notebook_id[:8]}.png"
            page.screenshot(path=str(screenshot_path))
            result["screenshot"] = str(screenshot_path)
            print(f"📸 Screenshot: {screenshot_path}")

            # Intentar obtener URLs del contenido generado
            try:
                links = page.query_selector_all('a[href*="drive.google"], a[href*="youtube"]')
                if links:
                    result["content_urls"] = [link.get_attribute("href") for link in links]
            except:
                pass

            if result["status"] not in ("ok", "cancelled"):
                result["status"] = "timeout"
                result["message"] = "Tiempo de espera agotado - verificar screenshot"

        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            try:
                error_screenshot = DATA_DIR / f"error_studio_{content_type}.png"
                page.screenshot(path=str(error_screenshot))
                result["error_screenshot"] = str(error_screenshot)
            except:
                pass

        finally:
            context.close()

    return result


def main():
    parser = argparse.ArgumentParser(description="Genera contenido del Studio de NotebookLM")
    parser.add_argument("--notebook-id", required=True, help="ID del cuaderno")
    parser.add_argument("--type", required=True, choices=list(CONTENT_TYPES.keys()),
                        help="Tipo de contenido a generar")
    parser.add_argument("--headless", action="store_true", help="Ejecutar sin ventana")
    parser.add_argument("--no-interactive", action="store_true",
                        help="Usar valores por defecto sin preguntar")
    parser.add_argument("--auto", action="store_true",
                        help="Generar automáticamente sin confirmación")
    parser.add_argument("--explore", action="store_true",
                        help="Solo explorar opciones disponibles, no generar")

    args = parser.parse_args()

    content_info = CONTENT_TYPES[args.type]

    if args.explore:
        print(f"\n🔍 Modo exploración: detectando opciones para {content_info['name']}...")
        print("   (No se generará contenido)")

    result = generate_content(
        notebook_id=args.notebook_id,
        content_type=args.type,
        headless=args.headless,
        interactive=not args.no_interactive,
        auto_generate=args.auto,
        explore_only=args.explore
    )

    # Mostrar resultado
    print(f"\n{'='*60}")
    print(f"RESULTADO: {result['status'].upper()}")
    print('='*60)

    if result["status"] == "ok":
        print(f"✅ {content_info['name']} generado correctamente")
        if "content_urls" in result:
            print(f"📎 URLs: {result['content_urls']}")
    elif result["status"] == "explored":
        print("🔍 Exploración completada")
        if "opciones_detectadas" in result:
            opts = result["opciones_detectadas"]
            if opts.get('formato'):
                print(f"   Formato: {', '.join(opts['formato'])}")
            if opts.get('idioma'):
                print(f"   Idioma: {opts['idioma']}")
            if opts.get('duracion'):
                print(f"   Duración: {', '.join(opts['duracion'])}")
            print(f"   Campo de prompt: {'Sí' if opts.get('tiene_prompt') else 'No'}")
    elif result["status"] == "cancelled":
        print("❌ Generación cancelada por el usuario")
    elif result["status"] == "error":
        print(f"❌ Error: {result.get('message', 'Desconocido')}")
    else:
        print(f"⚠️ {result.get('message', 'Verificar screenshot')}")

    if "screenshot" in result:
        print(f"📸 Screenshot final: {result['screenshot']}")
    if "dialog_screenshot" in result:
        print(f"📸 Screenshot diálogo: {result['dialog_screenshot']}")

    # Guardar resultado en JSON
    result_file = DATA_DIR / f"studio_result_{args.type}.json"
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"💾 Resultado guardado: {result_file}")


if __name__ == "__main__":
    main()
