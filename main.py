# main.py
# VERSIONE FINALE CON INDENTAZIONE CORRETTA

import json
import requests
import traceback
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti", "Walls", "Floors"]
OPENING_CATEGORIES = ["Porte", "Finestre", "Doors", "Windows"]
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"
PARAMETER_GROUP = "Testo"

COST_PARAMETER = "Costo_Unitario"
BUDGETS = {"Pavimenti": 50000, "Muri": 120000, "Floors": 50000, "Walls": 120000}
#=====================================================================================

#============== FUNZIONE DI RICERCA ELEMENTI =========================================
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

#============== FUNZIONI DI SUPPORTO =================================================
def get_ai_suggestion(prompt: str, api_key: str) -> str:
    if not api_key or "INCOLLA_QUI" in api_key:
        return "ATTENZIONE: Chiave API di Gemini non configurata."
    
    print("Chiamata all'API di Gemini (simulata)...")
    # Qui andrà la vera implementazione della chiamata API
    return "Suggerimento AI: Verificare immediatamente le compartimentazioni antincendio e revisionare i costi dei muri."

def send_webhook_notification(webhook_url: str, title: str, description: str, color: int, fields: list):
    if not webhook_url or "INCOLLA_QUI" in webhook_url:
        print("ATTENZIONE: URL del Webhook non configurato.")
        return
    print(f"Invio notifica webhook (simulata): {title}")
    # Qui andrà la vera implementazione dell'invio della notifica
    pass

#============== LOGICA DELLE REGOLE =================================================
def get_parameter_value(element, group_name: str, param_name: str):
    try:
        return element["parameters"][group_name][param_name]["value"]
    except (AttributeError, KeyError, TypeError):
        try:
            return element['properties']['Parameters']['Instance Parameters'][group_name][param_name]['value']
        except (AttributeError, KeyError, TypeError):
            return None

def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    validation_errors = []
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in TARGET_CATEGORIES_RULE_1):
            value = get_parameter_value(el, PARAMETER_GROUP, FIRE_RATING_PARAM)
            if value is None or not str(value).strip():
                validation_errors.append(el)
    
    print(f"Rule #1 Finished. {len(validation_errors)} errors found.", flush=True)
    return validation_errors

def run_penetration_check(all_elements: list) -> list:
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION CHECK ---", flush=True)
    penetration_errors = []
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in OPENING_CATEGORIES):
            value = get_parameter_value(el, PARAMETER_GROUP, FIRE_SEAL_PARAM)
            if not isinstance(value, str) or value.strip().lower() != "si":
                penetration_errors.append(el)
    
    print(f"Rule #3 Finished. {len(penetration_errors)} errors found.", flush=True)
    return penetration_errors

def run_budget_check(all_elements: list) -> list:
    print("--- RUNNING RULE #4: BUDGET SANITY CHECK ---", flush=True)
    costs_by_category = {cat: 0 for cat in BUDGETS.keys()}
    for el in all_elements:
        category = getattr(el, 'category', '')
        if category in costs_by_category:
            cost_val = get_parameter_value(el, PARAMETER_GROUP, COST_PARAMETER)
            unit_cost = float(cost_val) if cost_val else 0
            volume = getattr(el, 'volume', 0)
            costs_by_category[category] += volume * unit_cost

    budget_alerts = []
    for category, total_cost in costs_by_category.items():
        if total_cost > BUDGETS[category]:
            overrun = total_cost - BUDGETS[category]
            message = f"Categoria '{category}': superato il budget di €{overrun:,.2f}"
            print(f"BUDGET ALERT: {message}", flush=True)
            budget_alerts.append(message)
    
    print(f"Rule #4 Finished. {len(budget_alerts)} budget issues found.", flush=True)
    return budget_alerts

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING VALIDATION SCRIPT ---", flush=True)
    
    try:
        # --- SOLUZIONE ALTERNATIVA PER LE CHIAVI ---
        # ❗ ATTENZIONE: INSERISCI LE TUE CHIAVI QUI SOTTO
        FALLBACK_GEMINI_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjegI" 
        FALLBACK_WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

        gemini_api_key = ctx.get_secret("GEMINI_API_KEY") or FALLBACK_GEMINI_KEY
        webhook_url = ctx.get_secret("DISCORD_WEBHOOK_URL") or FALLBACK_WEBHOOK_URL
        
        if gemini_api_key == FALLBACK_GEMINI_KEY:
            print("AVVISO: Utilizzo della chiave API di riserva (fallback) dal codice. Non sicuro!", flush=True)
        if webhook_url == FALLBACK_WEBHOOK_URL:
            print("AVVISO: Utilizzo dell'URL Webhook di riserva (fallback) dal codice. Non sicuro!", flush=True)

        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("Validazione completata: Nessun elemento processabile trovato nel commit.")
            return

        print(f"Trovati {len(all_elements)} elementi totali da analizzare.", flush=True)

        fire_rating_errors = run_fire_rating_check(all_elements)
        penetration_errors = run_penetration_check(all_elements)
        budget_alerts = run_budget_check(all_elements)
        
        total_issues = len(fire_rating_errors) + len(penetration_errors) + len(budget_alerts)

        if total_issues > 0:
            summary_description = "Sono stati riscontrati i seguenti problemi nel modello:"
            fields = []
            
            if fire_rating_errors:
                fields.append({"name": f"Dato Mancante: Fire Rating ({len(fire_rating_errors)} elementi)", "value": f"Manca il parametro '{FIRE_RATING_PARAM}' su alcuni Muri o Pavimenti.", "inline": False})
                ctx.attach_error_to_objects(
                    category=f"Dato Mancante: {FIRE_RATING_PARAM}",
                    object_ids=[e.id for e in fire_rating_errors],
                    message=f"Il parametro '{FIRE_RATING_PARAM}' è mancante o vuoto."
                )

            if penetration_errors:
                fields.append({"name": f"Compartimentazione Antincendio ({len(penetration_errors)} elementi)", "value": f"Alcune aperture non sono sigillate (il parametro '{FIRE_SEAL_PARAM}' deve essere 'Si').", "inline": False})
                ctx.attach_warning_to_objects(
                    category="Apertura non Sigillata",
                    object_ids=[e.id for e in penetration_errors],
                    message=f"Questa apertura richiede una sigillatura. Il parametro '{FIRE_SEAL_PARAM}' deve essere 'Si'."
                )

            if budget_alerts:
                fields.append({"name": f"Superamento Budget ({len(budget_alerts)} categorie)", "value": "\n".join(budget_alerts), "inline": False})

            ai_prompt = (
                "Agisci come un BIM Manager esperto. "
                "Un controllo automatico ha trovato i seguenti problemi in un modello. "
                "Fornisci un commento conciso e un'azione prioritaria da comunicare al team. "
                f"Problemi Rilevati:\n" + "\n".join([f["name"] for f in fields])
            )
            ai_suggestion = get_ai_suggestion(ai_prompt, gemini_api_key)
            fields.append({"name": "🤖 Suggerimento del BIM Manager (AI)", "value": ai_suggestion, "inline": False})

            send_webhook_notification(webhook_url, "🚨 Validazione Modello Fallita", summary_description, 15158332, fields)
            
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
