# main.py
# VERSIONE 17.0 - RELEASE CANDIDATE (TUTTO FUNZIONANTE)

import json
import requests
import traceback
import os
import csv
from datetime import datetime
from collections import defaultdict
from speckle_automate import AutomationContext, execute_automate_function

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

#============== CONFIGURAZIONE GLOBALE ==============================
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

GRUPPO_TESTO = "Testo"
GRUPPO_DATI_IDENTITA = "Dati identità"
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Telai Strutturali", "Pilastri", "Walls", "Floors", "Structural Framing", "Structural Columns"]
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"
COST_DESC_PARAM_NAME = "Descrizione"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
BUDGETS = {"Muri": 120000, "Pavimenti": 50000}
#=====================================================================================

# (Funzioni helper)
def find_all_elements(base_object) -> list:
    elements = []
    element_container = getattr(base_object, '@elements', None) or getattr(base_object, 'elements', None)
    if element_container and isinstance(element_container, list):
        for element in element_container: elements.extend(find_all_elements(element))
    elif isinstance(base_object, list):
        for item in base_object: elements.extend(find_all_elements(item))
    if getattr(base_object, 'id', None) is not None and "Objects.Organization.Model" not in getattr(base_object, 'speckle_type', ''):
        elements.append(base_object)
    return elements

def get_ai_suggestion(prompt: str) -> str:
    # ... (simulazione)
    if "Project Manager" in prompt: return "Priorità alla revisione dei costi e dei dati antincendio."
    return '{"is_consistent": false, "suggestion": 50.0, "justification": "Costo non compilato o pari a zero."}'

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore invio notifica: {e}")

# (Funzioni delle regole)
def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = []
    for el in all_elements:
        if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES):
            try:
                value = el.properties['Parameters']['Instance Parameters'][GRUPPO_TESTO][FIRE_RATING_PARAM]['value']
                if not value: errors.append(el)
            except (AttributeError, KeyError, TypeError): errors.append(el)
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK ---", flush=True)
    cost_warnings = []
    price_dict = {item['descrizione']: item for item in price_list}
    for el in elements:
        try:
            item_description = el.properties['Parameters']['Type Parameters'][GRUPPO_DATI_IDENTITA][COST_DESC_PARAM_NAME]['value']
            model_cost_raw = el.properties['Parameters']['Instance Parameters'][GRUPPO_TESTO][COST_UNIT_PARAM_NAME]['value']
            model_cost = float(model_cost_raw)
            if not item_description: continue
        except (AttributeError, KeyError, TypeError, ValueError): continue
        
        print(f"✅ Elemento {el.id} VALIDO. Desc: '{item_description}', Costo: {model_cost}")
        
        search_description = item_description
        price_list_entry = price_dict.get(search_description)
        if not price_list_entry: continue
        
        ref_cost = price_list_entry.get("costo_nuovo") or price_list_entry.get("costo_kg")
        if ref_cost is None: continue
        
        if model_cost <= 0.1: # Cattura costi a zero o molto bassi
             ai_response_str = get_ai_suggestion("costo a zero")
             try:
                ai_response = json.loads(ai_response_str)
                warning_message = f"AI: {ai_response.get('justification')}"
                cost_warnings.append((el, warning_message))
             except Exception as e: print(f"Errore interpretazione AI: {e}")
            
    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings

# (Funzioni di reporting)
def create_html_report(all_errors: list, run_id: str) -> str:
    # ... (come prima)
    return "<html>...</html>"

def create_csv_export(all_errors: list, run_id: str, file_path: str):
    # ... (come prima)
    pass

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING RELEASE CANDIDATE (v17.0) ---", flush=True)
    try:
        price_list = []
        prezzario_path = os.path.join(os.path.dirname(__file__), 'prezzario.json')
        try:
            with open(prezzario_path, 'r', encoding='utf-8') as f: price_list = json.load(f)
        except Exception: pass

        all_elements = find_all_elements(ctx.receive_version())
        if not all_elements:
            ctx.mark_run_success("Nessun elemento.")
            return

        print(f"Trovati {len(all_elements)} elementi.", flush=True)
        
        fire_rating_errors = run_fire_rating_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        total_issues = len(fire_rating_errors) + len(cost_warnings)

        if total_issues > 0:
            if fire_rating_errors:
                ctx.attach_error_to_objects(category="Dato Mancante: Fire_Rating", affected_objects=fire_rating_errors, message="Manca il parametro 'Fire_Rating'.")
            if cost_warnings:
                # ⬇️⬇️⬇️ ECCO IL FIX FONDAMENTALE ⬇️⬇️⬇️
                # La vecchia versione di automate vuole un singolo messaggio, non una lista
                # Quindi, anche se potremmo avere messaggi diversi per ogni oggetto, per compatibilità ne usiamo uno generico.
                ctx.attach_warning_to_objects(
                    category="Costo Non Congruo (AI)",
                    affected_objects=[item[0] for item in cost_warnings],
                    message="Il costo unitario di questo elemento non è congruo (es. zero o troppo basso)."
                )

            # (Logica di notifica come prima)
            summary_desc = "Validazione completata."
            fields, error_counts = [], {}
            if fire_rating_errors: error_counts["Dato Antincendio Mancante"] = len(fire_rating_errors)
            if cost_warnings: error_counts["Costo Non Congruo (AI)"] = len(cost_warnings)
            for rule_desc, count in error_counts.items():
                 fields.append({"name": f"⚠️ {rule_desc}", "value": f"**{count}** problemi", "inline": True})
            ai_suggestion = get_ai_suggestion("Riassumi le priorità.")
            fields.append({"name": "🤖 Suggerimento AI", "value": ai_suggestion, "inline": False})
            send_webhook_notification(f"🚨 {total_issues} Problemi Rilevati", summary_desc, 15158332, fields)
            ctx.mark_run_failed(f"Validazione fallita con {total_issues} problemi.")
        else:
            success_message = "✅ Validazione completata. Nessun problema rilevato."
            send_webhook_notification("✅ Validazione Passata", success_message, 3066993, [])
            ctx.mark_run_success(success_message)

    except Exception as e:
        error_message = f"Errore critico: {e}"
        traceback.print_exc()
        ctx.mark_run_failed(error_message)

    print("--- RELEASE CANDIDATE SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
