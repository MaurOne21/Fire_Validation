# main.py
# VERSIONE 11.4 - ULTRA-COMPATIBILE (SPARTAN MODE)

import json
import requests
import traceback
import os
import csv
from datetime import datetime
from speckle_automate import AutomationContext, execute_automate_function

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

#============== CONFIGURAZIONE GLOBALE E CHIAVI SEGRETE ==============================
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

# --- Regole Antincendio ---
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Walls", "Floors", "Structural Framing", "Structural Columns"]
FIRE_OPENING_CATEGORIES = ["Porte", "Finestre", "Doors", "Windows"]
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"
COST_PARAM_GROUP_FIRE = "Testo" # Gruppo parametri per regole antincendio

# --- Regole Costi ---
COST_DESC_PARAM_NAME = "Descrizione"
COST_DESC_PARAM_GROUP = "Dati identità"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
COST_PARAM_GROUP_COST = "Testo" # Gruppo parametri per regole costi
BUDGETS = {"Muri": 120000, "Pavimenti": 50000, "Walls": 120000, "Floors": 50000}
#=====================================================================================

# (Le funzioni helper e delle regole rimangono identiche)
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

def get_type_parameter_value(element, group_name: str, param_name: str):
    try: return element.properties['Parameters']['Type Parameters'][group_name][param_name]['value']
    except (AttributeError, KeyError, TypeError): return None

def get_instance_parameter_value(element, group_name: str, param_name: str):
    try: return element.properties['Parameters']['Instance Parameters'][group_name][param_name]['value']
    except (AttributeError, KeyError, TypeError): return None

def get_ai_suggestion(prompt: str) -> str:
    if not GEMINI_API_KEY or "INCOLLA_QUI" in GEMINI_API_KEY:
        if "Project Manager" in prompt: return "AI non configurata."
        return '{"is_consistent": true, "justification": "AI non configurata."}'
    print(f"Chiamata all'API di Gemini (simulata)...")
    if "Project Manager" in prompt:
        return "Rischio budget elevato. Revisionare i costi."
    try:
        model_cost_str = prompt.split("Costo Modello: €")[1].split(" ")[0]
        model_cost = float(model_cost_str)
        if model_cost < 30.0:
            return '{"is_consistent": false, "suggestion": 45.50, "justification": "Costo troppo basso."}'
    except (IndexError, ValueError): pass
    return '{"is_consistent": true, "justification": "Costo congruo."}'

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    print(f"Invio notifica webhook a Discord: {title}")
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore durante l'invio della notifica a Discord: {e}")

def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES) and not get_instance_parameter_value(el, COST_PARAM_GROUP_FIRE, FIRE_RATING_PARAM)]
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_penetration_check(all_elements: list) -> list:
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION ---", flush=True)
    errors = []
    for el in all_elements:
        if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_OPENING_CATEGORIES):
            value = get_instance_parameter_value(el, COST_PARAM_GROUP_FIRE, FIRE_SEAL_PARAM)
            if not (value is True or str(value).lower() in ["si", "yes", "true", "1"]):
                errors.append(el)
    print(f"Rule #3 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_total_budget_check(elements: list) -> list:
    print("--- RUNNING RULE #4: TOTAL BUDGET CHECK ---", flush=True)
    costs_by_category = {cat: 0 for cat in BUDGETS.keys()}
    for el in elements:
        category = getattr(el, 'category', '')
        if category in costs_by_category:
            cost_val = get_instance_parameter_value(el, COST_PARAM_GROUP_COST, COST_UNIT_PARAM_NAME)
            metric = getattr(el, 'volume', getattr(el, 'area', 0))
            costs_by_category[category] += (float(cost_val) if cost_val else 0) * metric
    alerts = [f"Categoria '{cat}': superato budget di €{costs_by_category[cat] - BUDGETS[cat]:,.2f}" for cat in costs_by_category if costs_by_category[cat] > BUDGETS[cat]]
    print(f"Rule #4 Finished. {len(alerts)} budget issues found.", flush=True)
    return alerts

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK ---", flush=True)
    cost_warnings, price_dict = [], {item['descrizione']: item for item in price_list}
    for el in elements:
        item_description = get_type_parameter_value(el, COST_DESC_PARAM_GROUP, COST_DESC_PARAM_NAME)
        if not item_description: continue
        try: model_cost = float(get_instance_parameter_value(el, COST_PARAM_GROUP_COST, COST_UNIT_PARAM_NAME))
        except (ValueError, TypeError): continue
        phase_demolished = getattr(el, 'phaseDemolished', 'N/A')
        is_demolished = phase_demolished != 'N/A' and phase_demolished != 'None'
        search_description = item_description + " (DEMOLIZIONE)" if is_demolished else item_description
        price_list_entry = price_dict.get(search_description)
        if not price_list_entry: continue
        if 'densita_kg_m3' in price_list_entry: _, ref_cost, _ = ("costo_demolizione_kg", price_list_entry.get("costo_demolizione_kg"), "€/kg") if is_demolished else ("costo_kg", price_list_entry.get("costo_kg"), "€/kg")
        else: _, ref_cost, _ = ("costo_demolizione", price_list_entry.get("costo_demolizione"), f"€/{price_list_entry.get('unita', 'cad')}") if is_demolished else ("costo_nuovo", price_list_entry.get("costo_nuovo"), f"€/{price_list_entry.get('unita', 'cad')}")
        if ref_cost is None: continue
        ai_prompt = "..." # Omesso
        ai_response_str = get_ai_suggestion(ai_prompt)
        try:
            ai_response = json.loads(ai_response_str)
            if not ai_response.get("is_consistent"):
                warning_message = f"AI: {ai_response.get('justification')} (Suggerito: ~€{ai_response.get('suggestion'):.2f})"
                cost_warnings.append((el, warning_message))
        except Exception as e: print(f"Errore interpretazione AI: {e}")
    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings

def create_html_report(all_errors: list, commit_id: str) -> str:
    # ... (logica di creazione report)
    return "<html>...</html>" # Omesso per brevità

def create_csv_export(all_errors: list, commit_id: str, file_path: str):
    if not all_errors: return
    # Rimosse le colonne problematiche
    fieldnames = ["timestamp", "commit_id", "rule_id", "rule_description", "element_id", "element_category", "error_level", "message", "penalty_score"]
    with open(file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for error in all_errors:
            row = {"commit_id": commit_id, **error, "timestamp": datetime.utcnow().isoformat(), "penalty_score": 10 if error["error_level"] == "ERROR" else 3}
            final_row = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(final_row)

#============== ORCHESTRATORE PRINCIPALE (ULTRA-COMPATIBILE) =======================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING MASTER VALIDATION SCRIPT (ULTRA-COMPATIBLE) ---", flush=True)
    try:
        price_list = []
        prezzario_path = os.path.join(os.path.dirname(__file__), 'prezzario.json')
        try:
            with open(prezzario_path, 'r', encoding='utf-8') as f: price_list = json.load(f)
            print("Prezzario 'prezzario.json' caricato.")
        except Exception as e: print(f"ATTENZIONE: 'prezzario.json' non trovato: {e}")

        # ⬇️⬇️⬇️ MODIFICA CHIAVE: Usiamo solo ctx.version_id, che sappiamo funzionare ⬇️⬇️⬇️
        commit_id = ctx.version_id
        
        all_elements = find_all_elements(ctx.receive_version())
        if not all_elements:
            ctx.mark_run_success("Nessun elemento processabile.")
            return

        print(f"Trovati {len(all_elements)} elementi da analizzare.", flush=True)
        
        fire_rating_errors = run_fire_rating_check(all_elements)
        penetration_errors = run_penetration_check(all_elements)
        budget_alerts = run_total_budget_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        all_errors_structured = []
        for el in fire_rating_errors:
            all_errors_structured.append({"rule_id": "FIRE-01", "rule_description": "Dato Antincendio Mancante", "element_id": el.id, "element_category": getattr(el, 'category', 'N/A'), "error_level": "ERROR", "message": f"Manca '{FIRE_RATING_PARAM}'."})
        for el in penetration_errors:
            all_errors_structured.append({"rule_id": "FIRE-03", "rule_description": "Apertura non Sigillata", "element_id": el.id, "element_category": getattr(el, 'category', 'N/A'), "error_level": "WARNING", "message": f"'{FIRE_SEAL_PARAM}' non valido."})
        for msg in budget_alerts:
             all_errors_structured.append({"rule_id": "BUDGET-04", "rule_description": "Superamento Budget", "element_id": "N/A", "element_category": msg.split("'")[1], "error_level": "ERROR", "message": msg})
        for el, ai_msg in cost_warnings:
            all_errors_structured.append({"rule_id": "COST-05", "rule_description": "Costo Non Congruo (AI)", "element_id": el.id, "element_category": getattr(el, 'category', 'N/A'), "error_level": "WARNING", "message": ai_msg})

        total_issues = len(all_errors_structured)
        temp_path = os.path.dirname(ctx.speckle_token_path)
        
        # HTML Report (semplificato)
        html_report_path = os.path.join(temp_path, "validation_report.html")
        with open(html_report_path, "w", encoding='utf-8') as f: f.write(create_html_report(all_errors_structured, commit_id))
        
        # CSV Export (semplificato)
        csv_export_path = os.path.join(temp_path, "powerbi_export.csv")
        create_csv_export(all_errors_structured, commit_id, csv_export_path)
        
        ctx.store_result_blobs([html_report_path, csv_export_path])

        if total_issues > 0:
            summary_desc = f"Commit `{commit_id}`"
            fields, error_counts = [], {}
            for error in all_errors_structured:
                rule = error["rule_description"]
                error_counts[rule] = error_counts.get(rule, 0) + 1
            for rule_desc, count in error_counts.items():
                 fields.append({"name": f"⚠️ {rule_desc}", "value": f"**{count}** problemi", "inline": True})
            
            ai_prompt = "..." # Omesso
            ai_suggestion = get_ai_suggestion(ai_prompt)
            fields.append({"name": "🤖 Suggerimento AI", "value": ai_suggestion, "inline": False})
            
            send_webhook_notification(f"🚨 {total_issues} Problemi Rilevati", summary_desc, 15158332, fields)
            ctx.mark_run_failed(f"Validazione fallita con {total_issues} problemi.")
        else:
            success_message = "✅ Validazione completata. Nessun problema rilevato."
            print(success_message, flush=True)
            send_webhook_notification("✅ Validazione Passata", success_message, 3066993, [])
            ctx.mark_run_success(success_message)

    except Exception as e:
        error_message = f"Errore critico: {e}"
        traceback.print_exc()
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- MASTER VALIDATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
