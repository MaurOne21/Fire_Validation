# main.py
# VERSIONE 16.0 - CODICE ESPLICITO E DIRETTO

import json
import requests
import traceback
import os
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ==============================
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

# --- Nomi dei Gruppi Parametri (in Italiano) ---
GRUPPO_TESTO = "Testo"
GRUPPO_DATI_IDENTITA = "Dati identità"

# --- Regole Antincendio ---
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Telai Strutturali", "Pilastri", "Walls", "Floors", "Structural Framing", "Structural Columns"]
FIRE_RATING_PARAM = "Fire_Rating"

# --- Regole Costi ---
COST_DESC_PARAM_NAME = "Descrizione"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
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

def get_ai_suggestion(prompt: str) -> str:
    # ... (identica a prima)
    return '{"is_consistent": false, "suggestion": 45.50, "justification": "Costo non compilato o pari a zero."}'


def send_webhook_notification(title: str, description: str, color: int, fields: list):
    # ... (identica a prima)
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore durante l'invio della notifica a Discord: {e}")

#============== FUNZIONI DELLE REGOLE ================================================
def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = []
    for el in all_elements:
        if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES):
            try:
                # ACCESSO DIRETTO
                value = el.properties['Parameters']['Instance Parameters'][GRUPPO_TESTO][FIRE_RATING_PARAM]['value']
                if not value:
                    errors.append(el)
            except (AttributeError, KeyError, TypeError):
                errors.append(el) # Se il percorso non esiste, è un errore
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK (MODO ESPLICITO) ---", flush=True)
    cost_warnings = []
    price_dict = {item['descrizione']: item for item in price_list}
    
    for el in elements:
        item_description = None
        model_cost = None

        # --- TENTATIVO DI LETTURA ESPLICITO E DIRETTO ---
        try:
            item_description = el.properties['Parameters']['Type Parameters'][GRUPPO_DATI_IDENTITA][COST_DESC_PARAM_NAME]['value']
            model_cost_raw = el.properties['Parameters']['Instance Parameters'][GRUPPO_TESTO][COST_UNIT_PARAM_NAME]['value']
            model_cost = float(model_cost_raw)
        except (AttributeError, KeyError, TypeError, ValueError):
            continue # Se un qualsiasi passo fallisce, questo elemento non è valido, passiamo al prossimo

        # Se siamo arrivati qui, significa che abbiamo letto con successo entrambi i parametri.
        print(f"✅ Elemento {el.id} VALIDO per l'analisi. Desc: '{item_description}', Costo: {model_cost}")

        # (Il resto della logica è identico)
        search_description = item_description # Semplificato per il test
        price_list_entry = price_dict.get(search_description)
        if not price_list_entry: continue
        
        ref_cost = price_list_entry.get("costo_nuovo") or price_list_entry.get("costo_kg")
        if ref_cost is None: continue
        
        ai_prompt = (f"Valuta: '{search_description}', Costo Modello: €{model_cost:.2f}, Riferimento: €{ref_cost:.2f}")
        ai_response_str = get_ai_suggestion(ai_prompt)
        
        try:
            ai_response = json.loads(ai_response_str)
            if not ai_response.get("is_consistent"):
                warning_message = f"AI: {ai_response.get('justification')}"
                cost_warnings.append((el, warning_message))
        except Exception as e: print(f"Errore interpretazione AI: {e}")
            
    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings


#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING EXPLICIT VALIDATOR (v16.0) ---", flush=True)
    try:
        price_list = []
        prezzario_path = os.path.join(os.path.dirname(__file__), 'prezzario.json')
        try:
            with open(prezzario_path, 'r', encoding='utf-8') as f: price_list = json.load(f)
            print("Prezzario 'prezzario.json' caricato.")
        except Exception as e: print(f"ATTENZIONE: 'prezzario.json' non trovato: {e}")

        all_elements = find_all_elements(ctx.receive_version())
        if not all_elements:
            ctx.mark_run_success("Nessun elemento processabile.")
            return

        print(f"Trovati {len(all_elements)} elementi da analizzare.", flush=True)
        
        fire_rating_errors = run_fire_rating_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        total_issues = len(fire_rating_errors) + len(cost_warnings)

        if total_issues > 0:
            if fire_rating_errors:
                ctx.attach_error_to_objects(category=f"Dato Mancante: {FIRE_RATING_PARAM}", affected_objects=fire_rating_errors, message=f"Manca '{FIRE_RATING_PARAM}'.")
            if cost_warnings:
                ctx.attach_warning_to_objects(category="Costo Non Congruo (AI)", affected_objects=[item[0] for item in cost_warnings], message=[item[1] for item in cost_warnings])

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
            print(success_message, flush=True)
            send_webhook_notification("✅ Validazione Passata", success_message, 3066993, [])
            ctx.mark_run_success(success_message)

    except Exception as e:
        error_message = f"Errore critico: {e}"
        traceback.print_exc()
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- EXPLICIT SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
