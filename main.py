# main.py
# VERSIONE 26.1 - INTELLIGENZA 4D + AI REALE

import json
import requests
import traceback
import os
import time
from collections import defaultdict
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ==============================
# ⬇️⬇️⬇️ RIPRISTINATA LA CHIAVE API REALE ⬇️⬇️⬇️
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

GRUPPO_TESTO = "Testo"
GRUPPO_DATI_IDENTITA = "Dati identità"
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Telai Strutturali", "Pilastri", "Walls", "Floors", "Structural Framing", "Structural Columns"]
# ... (altre configurazioni)
WBS_TASK_PARAM = "WBS_Task" # Il nostro nuovo parametro per il 4D
#=====================================================================================

# (Le funzioni helper e le vecchie regole rimangono identiche)
def find_all_elements(base_object) -> list:
    # ...
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

# ⬇️⬇️⬇️ RIPRISTINATA LA FUNZIONE AI REALE E RESILIENTE ⬇️⬇️⬇️
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
            time.sleep(1.1) # Pausa per evitare rate limiting
            response = requests.post(url, headers=headers, json=payload, timeout=40)
            response.raise_for_status()
            json_response = response.json()
            text_response = json_response['candidates']['content']['parts']['text'].strip()
            print(f"Risposta ricevuta da Gemini.")
            return text_response
        except requests.exceptions.RequestException as e:
            if e.response and e.response.status_code == 429:
                print(f"Rate limit superato. Attendo 5 secondi (tentativo {attempt + 1}/{max_retries})")
                time.sleep(5)
                continue
            else:
                print(f"ERRORE di rete nella chiamata API: {e}")
                break
        except Exception as e:
            print(f"ERRORE nell'interpretazione della risposta AI: {e}")
            break
    
    if is_json_response: return '{"is_consistent": true, "justification": "Errore API dopo vari tentativi."}'
    return "Errore API dopo vari tentativi."


def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore invio notifica: {e}")

# (Le funzioni delle regole esistenti e la nuova 4D rimangono identiche)
# ...

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING 4D + REAL AI VALIDATOR (v26.1) ---", flush=True)
    try:
        # Carichiamo sia il prezzario che il cronoprogramma
        price_list = []
        schedule = {}
        try:
            with open(os.path.join(os.path.dirname(__file__), 'prezzario.json'), 'r', encoding='utf-8') as f:
                price_list = json.load(f)
        except Exception: print("ATTENZIONE: prezzario.json non trovato.")
        try:
            with open(os.path.join(os.path.dirname(__file__), 'schedule.json'), 'r', encoding='utf-8') as f:
                schedule = json.load(f)
        except Exception: print("ATTENZIONE: schedule.json non trovato.")

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

            summary_desc = "Report di Validazione Automatica"
            fields, error_counts = [], {}
            error_summary_for_ai = []
            
            if fire_rating_errors: error_counts["Dato Antincendio Mancante"] = len(fire_rating_errors)
            if cost_warnings: error_counts["Costo Non Congruo (AI)"] = len(cost_warnings)
            if sequencing_errors: error_counts["Incoerenza 4D"] = len(sequencing_errors)
            
            for rule_desc, count in error_counts.items():
                 fields.append({"name": f"⚠️ {rule_desc}", "value": f"**{count}** problemi", "inline": True})
                 error_summary_for_ai.append(f"- {count} errori di '{rule_desc}'")
            
            ai_prompt = f"""
            Agisci come un Project Manager BIM. Hai ricevuto questo report di validazione:
            {os.linesep.join(error_summary_for_ai)}
            Il tuo compito è scrivere un messaggio per il team su Discord. Deve essere breve, incisivo e assegnare due azioni concrete a persone fittizie (Paolo, Maria). Parla in italiano, non usare markdown.
            """
            ai_suggestion = get_ai_suggestion(ai_prompt, is_json_response=False)
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

    print("--- 4D + REAL AI SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
