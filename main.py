# main.py
# Versione finale con le Regole #1, #3 e #4.
# AGGIORNAMENTO: Centralizzata la logica di notifica per inviare un unico report riassuntivo.

import json
import requests
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
# ❗ INSERISCI QUI LE TUE CHIAVI!
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

# --- Regole ---
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti"]
OPENING_CATEGORIES = ["Porte", "Finestre"] 
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"
PARAMETER_GROUP = "Testo"

# --- Regola #4 ---
COST_PARAMETER = "Costo_Unitario"
BUDGETS = { "Pavimenti": 50000, "Muri": 120000 }
#=====================================================================================


def find_all_elements(base_object) -> list:
    # ... (funzione find_all_elements, omessa per brevità)
    return []

#============== FUNZIONI DI SUPPORTO ==================================================
def get_ai_suggestion(prompt: str) -> str:
    # ... (funzione get_ai_suggestion, omessa per brevità)
    return "AI suggestion placeholder"

def send_webhook_notification(ctx: AutomationContext, title: str, description: str, color: int, fields: list):
    # ... (funzione send_webhook_notification, omessa per brevità)
    pass

#============== LOGICA DELLE REGOLE ==================================================
def run_fire_rating_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #1. Restituisce una lista di oggetti con errore.
    """
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    validation_errors = []
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in TARGET_CATEGORIES_RULE_1):
            try:
                properties = getattr(el, 'properties')
                revit_parameters = properties['Parameters']
                instance_params = revit_parameters['Instance Parameters']
                text_group = instance_params[PARAMETER_GROUP]
                fire_rating_param_dict = text_group[FIRE_RATING_PARAM]
                value = fire_rating_param_dict.get("value")
                if value is None or not str(value).strip():
                    raise ValueError("Parameter value is missing or empty.")
            except (AttributeError, KeyError, ValueError):
                validation_errors.append(el)
    
    print(f"Rule #1 Finished. {len(validation_errors)} errors found.", flush=True)
    return validation_errors

def run_penetration_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #3. Restituisce una lista di oggetti con errore.
    """
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION CHECK ---", flush=True)
    penetration_errors = []
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in OPENING_CATEGORIES):
            is_sealed = False
            try:
                properties = getattr(el, 'properties', {})
                revit_parameters = properties.get('Parameters', {})
                instance_params = revit_parameters.get('Instance Parameters', {})
                text_group = instance_params.get(PARAMETER_GROUP, {})
                seal_param_dict = text_group.get(FIRE_SEAL_PARAM)
                if seal_param_dict:
                    value = seal_param_dict.get("value")
                    if isinstance(value, str) and value.strip().lower() == "si":
                        is_sealed = True
            except Exception:
                pass
            if not is_sealed:
                penetration_errors.append(el)
    
    print(f"Rule #3 Finished. {len(penetration_errors)} errors found.", flush=True)
    return penetration_errors

def run_budget_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #4. Restituisce una lista di messaggi di errore.
    """
    print("--- RUNNING RULE #4: BUDGET SANITY CHECK ---", flush=True)
    costs_by_category = {}
    for el in all_elements:
        category = getattr(el, 'category', '')
        if category in BUDGETS:
            try:
                properties = getattr(el, 'properties', {})
                revit_parameters = properties.get('Parameters', {})
                instance_params = revit_parameters.get('Instance Parameters', {})
                text_group = instance_params.get(PARAMETER_GROUP, {})
                cost_param = text_group.get(COST_PARAMETER, {})
                unit_cost = cost_param.get("value", 0)
                volume = getattr(el, 'volume', 0)
                if category not in costs_by_category:
                    costs_by_category[category] = 0
                costs_by_category[category] += volume * unit_cost
            except (AttributeError, KeyError):
                continue

    budget_alerts = []
    for category, total_cost in costs_by_category.items():
        budget = BUDGETS[category]
        if total_cost > budget:
            overrun = total_cost - budget
            message = f"Category '{category}' is over budget by €{overrun:.2f}"
            print(f"BUDGET ALERT: {message}", flush=True)
            budget_alerts.append(message)
    
    print(f"Rule #4 Finished. {len(budget_alerts)} budget issues found.", flush=True)
    return budget_alerts


#============== ORCHESTRATORE PRINCIPALE (AGGIORNATO) =================================
def main(ctx: AutomationContext) -> None:
    """
    Funzione principale che orchestra l'esecuzione di tutte le regole di validazione.
    """
    print("--- STARTING VALIDATION SCRIPT ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("No Revit elements found in the commit.")
            return

        print(f"Found {len(all_elements)} total elements to analyze.", flush=True)

        # Eseguiamo tutte le regole e raccogliamo i risultati
        fire_rating_errors = run_fire_rating_check(all_elements, ctx)
        penetration_errors = run_penetration_check(all_elements, ctx)
        budget_alerts = run_budget_check(all_elements, ctx)
        
        total_issues = len(fire_rating_errors) + len(penetration_errors) + len(budget_alerts)

        if total_issues > 0:
            # Costruiamo un unico report riassuntivo
            summary_description = "The following issues were found in the model:"
            fields = []
            
            if fire_rating_errors:
                fields.append({"name": f"Missing Fire Rating ({len(fire_rating_errors)} elements)", "value": "Some walls or floors are missing the 'Fire_Rating' parameter.", "inline": False})
                ctx.attach_error_to_objects(
                    category=f"Missing Data: {FIRE_RATING_PARAM}",
                    affected_objects=fire_rating_errors,
                    message=f"The parameter '{FIRE_RATING_PARAM}' is missing or empty."
                )

            if penetration_errors:
                fields.append({"name": f"Unsealed Fire Penetration ({len(penetration_errors)} elements)", "value": "Some openings require a fire seal ('FireSealInstalled' must be 'Si').", "inline": False})
                ctx.attach_warning_to_objects(
                    category="Unsealed Fire Penetration",
                    affected_objects=penetration_errors,
                    message=f"This opening requires a fire seal ('{FIRE_SEAL_PARAM}' parameter must be 'Si')."
                )

            if budget_alerts:
                fields.append({"name": f"Budget Overrun ({len(budget_alerts)} categories)", "value": "\n".join(budget_alerts), "inline": False})

            # Chiamiamo l'AI una sola volta con il riassunto
            ai_prompt = (
                "Agisci come un Direttore Lavori esperto. "
                "Dato il seguente riassunto di problemi di validazione in un modello BIM, "
                "fornisci un commento generale e un'azione prioritaria. "
                f"Problemi: {summary_description}\n" + "\n".join([f["name"] for f in fields])
            )
            ai_suggestion = get_ai_suggestion(ai_prompt)
            fields.append({"name": "🤖 Site Manager's Advice", "value": ai_suggestion, "inline": False})

            # Inviamo una sola notifica riassuntiva
            send_webhook_notification(ctx, "🚨 Validation Failed: Multiple Issues Found", summary_description, 15158332, fields)
            
            ctx.mark_run_failed(f"Validation failed with a total of {total_issues} issues.")
        else:
            ctx.mark_run_success("Validation passed: All rules were successful.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- VALIDATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
