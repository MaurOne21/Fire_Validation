# main.py
# VERSIONE FINALE E DEFINITIVA - COMPATIBILE CON AMBIENTI SPECKLE DATATI

import json
import requests
import traceback
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE E CHIAVI SEGRETE ==============================
# ❗❗❗ INSERISCI LE TUE CHIAVI QUI ❗❗❗
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

# --- Regole ---
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti", "Walls", "Floors"]
OPENING_CATEGORIES = ["Porte", "Finestre", "Doors", "Windows"]
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"
PARAMETER_GROUP = "Testo"

# --- Regola #4 ---
COST_PARAMETER = "Costo_Unitario"
BUDGETS = {"Pavimenti": 50000, "Muri": 120000, "Floors": 50000, "Walls": 120000}
#=====================================================================================

def find_all_elements(base_object) -> list:
    elements = []
    element_container = getattr(base_object, '@elements', None) or getattr(base_object, 'elements', None)
    if element_container and isinstance(element_container, list):
        for element in element_container:
            elements.extend(find_all_elements(element))
    elif isinstance(base_object, list):
        for item in base_object:
            elements.extend(find_all_elements(item))
    if getattr(base_object, 'id', None) is not None:
        if "Objects.Organization.Model" not in getattr(base_object, 'speckle_type', ''):
            elements.append(base_object)
    return elements

def get_ai_suggestion(prompt: str) -> str:
    if not GEMINI_API_KEY or "INCOLLA_QUI" in GEMINI_API_KEY:
        return "ATTENZIONE: Chiave API di Gemini non configurata."
    print("Chiamata all'API di Gemini (simulata)...")
    return "Suggerimento AI: Verificare immediatamente le compartimentazioni antincendio e revisionare i costi dei muri."

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL:
        print("ATTENZIONE: URL del Webhook non configurato.")
        return
    print(f"Invio notifica webhook a Discord: {title}")
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    requests.post(WEBHOOK_URL, json={"embeds": [embed]})

def get_parameter_value(element, group_name: str, param_name: str):
    try: return element["parameters"][group_name][param_name]["value"]
    except (AttributeError, KeyError, TypeError):
        try: return element['properties']['Parameters']['Instance Parameters'][group_name][param_name]['value']
        except (AttributeError, KeyError, TypeError): return None

def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in TARGET_CATEGORIES_RULE_1) and (get_parameter_value(el, PARAMETER_GROUP, FIRE_RATING_PARAM) is None or not str(get_parameter_value(el, PARAMETER_GROUP, FIRE_RATING_PARAM)).strip())]
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_penetration_check(all_elements: list) -> list:
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION CHECK ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in OPENING_CATEGORIES) and (not isinstance(get_parameter_value(el, PARAMETER_GROUP, FIRE_SEAL_PARAM), str) or get_parameter_value(el, PARAMETER_GROUP, FIRE_SEAL_PARAM).strip().lower() != "si")]
    print(f"Rule #3 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_budget_check(all_elements: list) -> list:
    print("--- RUNNING RULE #4: BUDGET SANITY CHECK ---", flush=True)
    costs = {cat: 0 for cat in BUDGETS.keys()}
    for el in all_elements:
        cat = getattr(el, 'category', '')
        if cat in costs:
            cost_val = get_parameter_value(el, PARAMETER_GROUP, COST_PARAMETER)
            costs[cat] += (float(cost_val) if cost_val else 0) * getattr(el, 'volume', 0)
    alerts = [f"Categoria '{c}': superato budget di €{costs[c] - BUDGETS[c]:,.2f}" for c in costs if costs[c] > BUDGETS[c]]
    for alert in alerts: print(f"BUDGET ALERT: {alert}", flush=True)
    print(f"Rule #4 Finished. {len(alerts)} budget issues found.", flush=True)
    return alerts

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING VALIDATION SCRIPT ---", flush=True)
    try:
        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("Validazione completata: Nessun elemento processabile trovato nel commit.")
            return

        print(f"Trovati {len(all_elements)} elementi totali da analizzare.", flush=True)

        fire_rating_errors = run_fire_rating_check(all_elements)
        penetration_errors = run_penetration_check(all_elements)
        budget_alerts = run_budget_check(all_elements)
        
        # --- INIZIO BLOCCO DI DEBUG ---
# Stampiamo i dettagli del primo muro con errore per analizzarlo
if fire_rating_errors:
    print("\n--- DEBUG: ISPEZIONE PRIMO MURO CON ERRORE ---", flush=True)
    # Usiamo json.dumps per stampare l'oggetto in modo leggibile
    print(json.dumps(fire_rating_errors[0].to_dict(), indent=2))
    print("---------------------------------------------\n", flush=True)
# --- FINE BLOCCO DI DEBUG ---
        
        total_issues = len(fire_rating_errors) + len(penetration_errors) + len(budget_alerts)

        if total_issues > 0:
            summary_desc = "Sono stati riscontrati i seguenti problemi nel modello:"
            fields = []
            
            if fire_rating_errors:
                fields.append({"name": f"Dato Mancante: Fire Rating ({len(fire_rating_errors)} elementi)", "value": f"Manca il parametro '{FIRE_RATING_PARAM}'.", "inline": False})
                #  ⬇️⬇️⬇️  ECCO LA CORREZIONE  ⬇️⬇️⬇️
                ctx.attach_error_to_objects(category=f"Dato Mancante: {FIRE_RATING_PARAM}", affected_objects=fire_rating_errors, message=f"Il parametro '{FIRE_RATING_PARAM}' è mancante.")
            
            if penetration_errors:
                fields.append({"name": f"Compartimentazione ({len(penetration_errors)} elementi)", "value": f"Aperture non sigillate ('{FIRE_SEAL_PARAM}' non è 'Si').", "inline": False})
                #  ⬇️⬇️⬇️  ECCO LA CORREZIONE  ⬇️⬇️⬇️
                ctx.attach_warning_to_objects(category="Apertura non Sigillata", affected_objects=penetration_errors, message=f"Questa apertura non è sigillata.")

            if budget_alerts:
                fields.append({"name": f"Superamento Budget ({len(budget_alerts)} categorie)", "value": "\n".join(budget_alerts), "inline": False})

            ai_prompt = f"Agisci come un BIM Manager. Un controllo automatico ha trovato questi problemi: {', '.join([f['name'] for f in fields])}. Fornisci un commento e un'azione prioritaria."
            ai_suggestion = get_ai_suggestion(ai_prompt)
            fields.append({"name": "🤖 Suggerimento del BIM Manager (AI)", "value": ai_suggestion, "inline": False})

            send_webhook_notification("🚨 Validazione Modello Fallita", summary_desc, 15158332, fields)
            ctx.mark_run_failed(f"Validazione fallita con {total_issues} problemi totali.")
        else:
            success_message = "Validazione completata con successo. Tutti i controlli sono stati superati."
            print(success_message, flush=True)
            ctx.mark_run_success(success_message)

    except Exception as e:
        error_message = f"Errore critico durante l'esecuzione dello script: {e}"
        traceback.print_exc()
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- VALIDATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
