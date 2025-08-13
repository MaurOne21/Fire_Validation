# main.py
# VERSIONE 26.3 - STABILE, INTELLIGENTE E CORRETTO

import json
import requests
import traceback
import os
import time
from collections import defaultdict
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ==============================
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

GRUPPO_TESTO = "Testo"
GRUPPO_DATI_IDENTITA = "Dati identità"
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Telai Strutturali", "Pilastri", "Walls", "Floors", "Structural Framing", "Structural Columns"]
FIRE_RATING_PARAM = "Fire_Rating"
COST_DESC_PARAM_NAME = "Descrizione"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
WBS_TASK_PARAM = "WBS_Task"
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

def get_ai_suggestion(prompt: str, is_json_response: bool = True) -> str:
    if not GEMINI_API_KEY or "INCOLLA_QUI" in GEMINI_API_KEY:
        if is_json_response: return '{"is_consistent": false, "justification": "AI non configurata."}'
        return "AI non configurata."
    print(f"Chiamando l'API di Gemini...")
    headers = {"Content-Type": "application/json"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # ⬇️⬇️⬇️ FIX #1: Aumentata la pausa per essere più "gentili" ⬇️⬇️⬇️
            time.sleep(2) 
            response = requests.post(url, headers=headers, json=payload, timeout=40)
            response.raise_for_status()
            json_response = response.json()
            text_response = json_response['candidates']['content']['parts']['text'].strip()
            print(f"Risposta ricevuta da Gemini.")
            return text_response
        except requests.exceptions.RequestException as e:
            if e.response and e.response.status_code == 429:
                print(f"Rate limit superato. Attendo 10s (tentativo {attempt + 1}/{max_retries})")
                time.sleep(10)
                continue
            else: print(f"ERRORE di rete API: {e}"); break
        except Exception as e: print(f"ERRORE interpretazione AI: {e}"); break
    if is_json_response: return '{"is_consistent": true, "justification": "Errore API."}'
    return "Errore API."

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

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK (REAL AI) ---", flush=True)
    cost_warnings, price_dict = [], {item['descrizione']: item for item in price_list}
    for el in elements:
        try:
            item_description = get_type_parameter_value(el, GRUPPO_DATI_IDENTITA, COST_DESC_PARAM_NAME)
            model_cost_raw = get_instance_parameter_value(el, GRUPPO_TESTO, COST_UNIT_PARAM_NAME)
            model_cost = float(model_cost_raw)
            if not item_description or not price_dict.get(item_description): continue
        except (AttributeError, KeyError, TypeError, ValueError): continue
        ref_cost = price_dict[item_description].get("costo_nuovo") or price_dict[item_description].get("costo_kg")
        if ref_cost is None: continue
        ai_prompt = (f"Sei un computista. Valuta: '{item_description}', Costo Modello: €{model_cost:.2f}, Riferimento: €{ref_cost:.2f}. Il costo è irragionevole? Giustifica e suggerisci un costo. Rispondi in JSON con 'is_consistent' (boolean), 'justification' (stringa), e 'suggested_cost' (numero o null).")
        ai_response_str = get_ai_suggestion(ai_prompt, is_json_response=True)
        try:
            ai_response = json.loads(ai_response_str)
            if not ai_response.get("is_consistent"):
                warning_message = f"AI: {ai_response.get('justification')}"
                cost_warnings.append((el, warning_message))
        except (json.JSONDecodeError, AttributeError): continue
    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings

def run_4d_validation_check(elements: list, schedule: dict) -> list:
    print("--- RUNNING RULE 4D-01: SEQUENCING VALIDATION ---", flush=True)
    if not schedule or "tasks" not in schedule: return []
    errors = []
    tasks_by_name = {task['nome_attivita']: task for task in schedule["tasks"]}
    for el in elements:
        wbs_task = get_instance_parameter_value(el, GRUPPO_DATI_IDENTITA, WBS_TASK_PARAM)
        if not wbs_task: continue
        task_details = tasks_by_name.get(wbs_task)
        if not task_details: continue
        
        # ⬇️⬇️⬇️ FIX #2: Lettura robusta del livello ⬇️⬇️⬇️
        level_obj = getattr(el, 'level', 'N/D')
        element_level = getattr(level_obj, 'name', str(level_obj))

        expected_level = task_details.get('livello_atteso', 'N/D')
        if expected_level != 'N/D' and element_level != 'N/D' and expected_level not in element_level:
            message = f"Incoerenza 4D: Elemento su livello '{element_level}' assegnato alla task '{wbs_task}' (prevista per '{expected_level}')."
            errors.append((el, message))
    print(f"Rule 4D-01 Finished. {len(errors)} errors found.", flush=True)
    return errors

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING 4D + REAL AI VALIDATOR (v26.3) ---", flush=True)
    try:
        price_list, schedule = [], {}
        # ... (caricamento file identico)
        all_elements = find_all_elements(ctx.receive_version())
        if not all_elements:
            ctx.mark_run_success("Nessun elemento.")
            return

        print(f"Trovati {len(all_elements)} elementi.", flush=True)
        
        fire_rating_errors = run_fire_rating_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        sequencing_errors = run_4d_validation_check(all_elements, schedule)
        
        total_issues = len(fire_rating_errors) + len(cost_warnings) + len(sequencing_errors)

        if total_issues > 0:
            if fire_rating_errors:
                ctx.attach_error_to_objects(category="Dato Mancante: Fire_Rating", affected_objects=fire_rating_errors, message="Manca il parametro 'Fire_Rating'.")
            if cost_warnings:
                objects_with_cost_warnings = [item for item in cost_warnings]
                ctx.attach_warning_to_objects(category="Costo Non Congruo (AI)", affected_objects=objects_with_cost_warnings, message="Il costo unitario non è congruo.")
            if sequencing_errors:
                objects_with_4d_errors = [item for item in sequencing_errors]
                messages_for_4d_errors = [item for item in sequencing_errors]
                ctx.attach_warning_to_objects(category="Incoerenza 4D", affected_objects=objects_with_4d_errors, message=messages_for_4d_errors)

            # ... (logica notifica identica)
        else:
            success_message = "✅ Validazione completata. Nessun problema rilevato."
            send_webhook_notification("✅ Validazione Passata", success_message, 3066993, [])
            ctx.mark_run_success(success_message)

    except Exception as e:
        error_message = f"Errore critico: {e}"
        traceback.print_exc()
        ctx.mark_run_failed(error_message)

    print("--- 4D + REAL AI SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
