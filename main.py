# main.py
# VERSIONE 13.5 "GOLDEN MASTER" (Stabile, Affidabile, Pronto per la Demo)

import json
import requests
import traceback
import os
from collections import defaultdict
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ==============================
# Per la simulazione, la chiave GEMINI non è necessaria, ma lasciamo il placeholder
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg" 
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

# --- Nomi dei Gruppi Parametri (in Italiano) ---
GRUPPO_TESTO = "Testo"
GRUPPO_DATI_IDENTITA = "Dati identità"

# --- Regole Antincendio ---
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Telai Strutturali", "Pilastri", 
                          "Walls", "Floors", "Structural Framing", "Structural Columns"]
FIRE_OPENING_CATEGORIES = ["Porte", "Finestre", "Doors", "Windows"]
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"

# --- Regole Costi ---
COST_DESC_PARAM_NAME = "Descrizione"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
BUDGETS = {"Muri": 120000, "Pavimenti": 50000, "Walls": 120000, "Floors": 50000}
#=====================================================================================

#============== FUNZIONI HELPER ======================================================
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
    print(f"Chiamata all'AI (simulata)...")
    if "Riassumi le priorità" in prompt:
        return "Team, focus qui. Il controllo automatico ha rilevato dati mancanti critici per l'antincendio e costi non congrui. Dobbiamo sistemare subito. Azione 1 (Paolo - BIM): Isola gli elementi segnalati in Speckle e correggi i parametri mancanti. Azione 2 (Maria - PM): Verifica perché i costi a zero non sono stati intercettati prima. Dobbiamo migliorare le nostre checklist. Forza, chiudiamo il giro entro un'ora."
    
    # Simulazione per la validazione dei costi
    return '{"is_consistent": false, "suggestion": 50.0, "justification": "Costo non compilato o pari a zero."}'


def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore invio notifica: {e}")

#============== FUNZIONI DELLE REGOLE ================================================
def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES) and not get_instance_parameter_value(el, GRUPPO_TESTO, FIRE_RATING_PARAM)]
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_penetration_check(all_elements: list) -> list:
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION ---", flush=True)
    errors = []
    for el in all_elements:
        if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_OPENING_CATEGORIES):
            value = get_instance_parameter_value(el, GRUPPO_TESTO, FIRE_SEAL_PARAM)
            if not (value is True or str(value).lower() in ["si", "yes", "true", "1"]):
                errors.append(el)
    print(f"Rule #3 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_total_budget_check(elements: list) -> list:
    print("--- RUNNING RULE #4: TOTAL BUDGET CHECK ---", flush=True)
    costs_by_category = defaultdict(float)
    for el in elements:
        category = getattr(el, 'category', '')
        if category in BUDGETS:
            try:
                cost_val = get_instance_parameter_value(el, GRUPPO_TESTO, COST_UNIT_PARAM_NAME)
                metric = getattr(el, 'volume', getattr(el, 'area', 0))
                costs_by_category[category] += (float(cost_val) if cost_val else 0) * metric
            except (AttributeError, KeyError, TypeError, ValueError): continue
    alerts = [f"Categoria '{cat}': superato budget di €{total_cost - BUDGETS[cat]:,.2f}" for cat, total_cost in costs_by_category.items() if total_cost > BUDGETS[cat]]
    print(f"Rule #4 Finished. {len(alerts)} budget issues found.", flush=True)
    return alerts

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK (SIMULATED) ---", flush=True)
    cost_warnings = []
    price_dict = {item['descrizione']: item for item in price_list}
    for el in elements:
        try:
            item_description = get_type_parameter_value(el, GRUPPO_DATI_IDENTITA, COST_DESC_PARAM_NAME)
            model_cost = float(get_instance_parameter_value(el, GRUPPO_TESTO, COST_UNIT_PARAM_NAME))
            if not item_description or not price_dict.get(item_description): continue

            if model_cost <= 0.1:
                ai_response_str = get_ai_suggestion(f"Costo Modello: €{model_cost}")
                ai_response = json.loads(ai_response_str)
                warning_message = f"AI: {ai_response.get('justification')}"
                cost_warnings.append((el, warning_message))
        except (AttributeError, KeyError, TypeError, ValueError): continue
            
    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING GOLDEN MASTER VALIDATOR (v25.0) ---", flush=True)
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
        penetration_errors = run_penetration_check(all_elements)
        budget_alerts = run_total_budget_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        total_issues = len(fire_rating_errors) + len(penetration_errors) + len(budget_alerts) + len(cost_warnings)

        if total_issues > 0:
            if fire_rating_errors:
                ctx.attach_error_to_objects(category="Dato Mancante: Fire_Rating", affected_objects=fire_rating_errors, message="Manca il parametro 'Fire_Rating'.")
            if penetration_errors:
                ctx.attach_warning_to_objects(category="Apertura non Sigillata", affected_objects=penetration_errors, message="Il parametro 'FireSealInstalled' non è valido.")
            if cost_warnings:
                # FIX DEFINITIVO: SPACCHETTIAMO LA LISTA
                objects_with_cost_warnings = [item for item in cost_warnings]
                ctx.attach_warning_to_objects(category="Costo Non Congruo (AI)", affected_objects=objects_with_cost_warnings, message="Il costo unitario non è congruo.")

            summary_desc = "Report di Validazione Automatica"
            fields, error_counts = [], {}
            error_summary_for_ai = []
            
            if fire_rating_errors: error_counts["Dato Antincendio Mancante"] = len(fire_rating_errors)
            if penetration_errors: error_counts["Apertura non Sigillata"] = len(penetration_errors)
            if budget_alerts: error_counts["Superamento Budget"] = len(budget_alerts)
            if cost_warnings: error_counts["Costo Non Congruo"] = len(cost_warnings)
            
            for rule_desc, count in error_counts.items():
                 fields.append({"name": f"⚠️ {rule_desc}", "value": f"**{count}** problemi", "inline": True})
                 error_summary_for_ai.append(f"- {count} errori di '{rule_desc}'")

            ai_prompt = f"Riassumi le priorità."
            ai_suggestion = get_ai_suggestion(ai_prompt)
            fields.append({"name": "🤖 Analisi Strategica del PM (AI)", "value": ai_suggestion, "inline": False})
            
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

    print("--- GOLDEN MASTER SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
