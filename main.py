# main.py
# VERSIONE 23.1 - NOTIFICHE INTELLIGENTI E OPERATIVE

import json
import requests
import traceback
import os
from collections import defaultdict
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE (Stabile) ==================
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg" # Ora serve davvero!
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

GRUPPO_TESTO = "Testo"
GRUPPO_DATI_IDENTITA = "Dati identità"
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Telai Strutturali", "Pilastri", "Walls", "Floors", "Structural Framing", "Structural Columns"]
FIRE_RATING_PARAM = "Fire_Rating"
COST_DESC_PARAM_NAME = "Descrizione"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
# ... (altre configurazioni se necessarie)
#=====================================================================================

# (Tutte le funzioni helper e delle regole sono identiche alla v23.0, le ometto per brevità)
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

def get_ai_suggestion(prompt: str) -> str:
    # Questa volta usiamo la VERA funzione AI che avevamo costruito
    if not GEMINI_API_KEY or "INCOLLA_QUI" in GEMINI_API_KEY:
        return "AI non configurata. Impossibile generare il suggerimento."
    print(f"Chiamando l'API di Gemini...")
    headers = {"Content-Type": "application/json"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        response.raise_for_status()
        json_response = response.json()
        text_response = json_response['candidates']['content']['parts']['text'].strip()
        print(f"Risposta ricevuta da Gemini: {text_response}")
        return text_response
    except Exception as e:
        print(f"ERRORE nella chiamata AI: {e}")
        return "Errore durante la generazione del suggerimento AI."

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore invio notifica: {e}")

# (Le funzioni delle regole sono identiche)
# ...
def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES) and not get_instance_parameter_value(el, GRUPPO_TESTO, FIRE_RATING_PARAM)]
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK (SIMULATED) ---", flush=True)
    cost_warnings = []
    # ... (logica interna identica)
    return cost_warnings


#============== ORCHESTRATORE PRINCIPALE (con Logica di Notifica Avanzata) ===========
def main(ctx: AutomationContext) -> None:
    print("--- STARTING SMART NOTIFICATION VALIDATOR (v23.1) ---", flush=True)
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
        # Qui potremmo aggiungere le altre regole
        
        total_issues = len(fire_rating_errors) + len(cost_warnings)

        if total_issues > 0:
            if fire_rating_errors:
                ctx.attach_error_to_objects(category="Dato Mancante: Fire_Rating", affected_objects=fire_rating_errors, message="Manca il parametro 'Fire_Rating'.")
            if cost_warnings:
                objects_with_cost_warnings = [item for item in cost_warnings]
                ctx.attach_warning_to_objects(category="Costo Non Congruo (AI)", affected_objects=objects_with_cost_warnings, message="Il costo unitario non è congruo.")

            # --- COSTRUZIONE DEL REPORT PER L'AI E DISCORD ---
            summary_desc = f"Commit: `{ctx.version_id}`\nModello: `{ctx.model.name}`"
            fields = []
            error_summary_for_ai = []
            
            error_counts = defaultdict(int)
            for el in fire_rating_errors: error_counts["Dato Antincendio Mancante"] += 1
            for el, msg in cost_warnings: error_counts["Costo Non Congruo (AI)"] += 1
            
            for rule_desc, count in error_counts.items():
                 fields.append({"name": f"⚠️ {rule_desc}", "value": f"**{count}** problemi", "inline": True})
                 error_summary_for_ai.append(f"- {count} errori di '{rule_desc}'")
            
            # --- CHIAMATA ALL'AI PER IL SUGGERIMENTO STRATEGICO ---
            ai_prompt = f"""
            Agisci come un Project Manager BIM esperto, diretto e orientato alla soluzione. Hai appena ricevuto il seguente report di validazione automatica da un modello Speckle.

            **Report Errori:**
            {os.linesep.join(error_summary_for_ai)}

            **Il tuo compito:**
            Scrivi un messaggio breve e incisivo per il team sul canale Discord. Il messaggio deve:
            1. Iniziare con un richiamo all'azione (es. "Team, focus qui.").
            2. Riassumere il problema principale in termini chiari e non tecnici.
            3. Assegnare due azioni concrete e immediate a persone fittizie (es. Paolo per la modellazione, Maria per i processi).
            4. Concludere con un senso di urgenza.
            Il tono deve essere quello di un leader, non di un robot. Parla in italiano e non usare mai markdown.
            """
            
            ai_suggestion = get_ai_suggestion(ai_prompt)
            fields.append({"name": "🤖 Suggerimento del Project Manager (AI)", "value": ai_suggestion, "inline": False})
            
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

    print("--- SMART NOTIFICATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
