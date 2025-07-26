# main.py
# Versione finale con le Regole #1, #3 e la nuova, robusta Regola #4 (Controllo Budget).

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

# --- Nuova Regola #4 ---
COST_PARAMETER = "Costo_Unitario"
# Definiamo i budget per categoria. Puoi modificare questi valori.
BUDGETS = {
    "Pavimenti": 50000,
    "Muri": 120000,
}
#=====================================================================================


def find_all_elements(base_object) -> list:
    """
    Cerca ricorsivamente in un oggetto Speckle tutti gli elementi.
    """
    all_elements = []
    elements_property = getattr(base_object, 'elements', None)
    if not elements_property:
        elements_property = getattr(base_object, '@elements', None)

    if elements_property and isinstance(elements_property, list):
        for element in elements_property:
            all_elements.extend(find_all_elements(element))
    elif "Collection" not in getattr(base_object, "speckle_type", ""):
        all_elements.append(base_object)
    return all_elements


#============== FUNZIONI DI SUPPORTO ==================================================
def get_ai_suggestion(prompt: str) -> str:
    """
    Interroga l'API di Gemini per ottenere un suggerimento basato su un prompt.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "LA_TUA_CHIAVE_API_DI_GEMINI":
        return "AI suggestion not available (API key not configured)."

    print("Asking AI for a suggestion...", flush=True)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        suggestion = result["candidates"][0]["content"]["parts"][0]["text"]
        return suggestion
    except Exception as e:
        print(f"Could not get AI suggestion. Reason: {e}", flush=True)
        return "Could not retrieve AI suggestion at this time."

def send_webhook_notification(ctx: AutomationContext, title: str, description: str, color: int, fields: list):
    """
    Invia una notifica a un webhook di Discord con un messaggio personalizzato.
    """
    if not WEBHOOK_URL or WEBHOOK_URL == "IL_TUO_URL_DEL_WEBHOOK_DI_DISCORD":
        return

    print("Sending Discord webhook notification...", flush=True)
    
    trigger_payload = ctx.automation_run_data.triggers[0].payload
    model_id = trigger_payload.model_id
    version_id = trigger_payload.version_id
    commit_url = f"{ctx.speckle_client.url}/projects/{ctx.automation_run_data.project_id}/models/{model_id}@{version_id}"
    
    message = {
        "content": "New Speckle Automation Report!",
        "username": "Speckle Validator",
        "avatar_url": "https://speckle.systems/favicon.ico",
        "embeds": [{
            "title": title,
            "description": description,
            "url": commit_url,
            "color": color,
            "fields": fields,
            "footer": {"text": f"Commit ID: {version_id}"}
        }]
    }

    try:
        requests.post(WEBHOOK_URL, json=message)
    except Exception as e:
        print(f"Could not send Discord webhook notification. Reason: {e}", flush=True)


#============== LOGICA DELLE REGOLE ==================================================
def run_fire_rating_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #1: Verifica che tutti i muri e solai abbiano
    il parametro 'Fire_Rating' compilato.
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

    if validation_errors:
        error_description = f"{len(validation_errors)} elements are missing the '{FIRE_RATING_PARAM}' parameter."
        ai_prompt = (
            "Agisci come un Direttore Lavori italiano esperto e molto pratico. "
            "Dato il seguente problema di validazione rilevato in un modello BIM, "
            "fornisci due azioni correttive concrete e operative, come se stessi parlando al team in cantiere. "
            "Sii conciso e usa un formato markdown (lista puntata). "
            f"Problema: '{error_description}'."
        )
        ai_suggestion = get_ai_suggestion(ai_prompt)
        
        title = f"🚨 Validation Alert: Missing Data: {FIRE_RATING_PARAM}"
        description = f"A validation rule failed in project **{ctx.automation_run_data.project_id}**."
        fields = [
            {"name": "Model", "value": f"`{ctx.automation_run_data.triggers[0].payload.model_id}`", "inline": True},
            {"name": "Failed Elements", "value": str(len(validation_errors)), "inline": True},
            {"name": "🤖 Site Manager's Advice", "value": ai_suggestion, "inline": False},
        ]
        send_webhook_notification(ctx, title, description, 15158332, fields)

        ctx.attach_error_to_objects(
            category=f"Missing Data: {FIRE_RATING_PARAM}",
            affected_objects=validation_errors,
            message=f"The parameter '{FIRE_RATING_PARAM}' is missing or empty."
        )
    
    print(f"Rule #1 Finished. {len(validation_errors)} errors found.", flush=True)
    return validation_errors

def run_penetration_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #3: Controlla che tutte le porte/finestre abbiano
    la sigillatura specificata.
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
            except Exception as e:
                print(f"WARNING (Rule 3): Could not parse parameters for opening {el.id}. Reason: {e}", flush=True)
            if not is_sealed:
                penetration_errors.append(el)

    if penetration_errors:
        error_description = f"{len(penetration_errors)} openings require a fire seal ('{FIRE_SEAL_PARAM}' parameter must be 'Si')."
        ai_prompt = (
            "Agisci come un Direttore Lavori italiano esperto e molto pratico. "
            "Dato il seguente problema di validazione rilevato in un modello BIM, "
            "fornisci due azioni correttive concrete e operative, come se stessi parlando al team in cantiere. "
            "Sii conciso e usa un formato markdown (lista puntata). "
            f"Problema: '{error_description}'."
        )
        ai_suggestion = get_ai_suggestion(ai_prompt)

        title = "🚨 Validation Alert: Unsealed Fire Penetration"
        description = f"A validation rule failed in project **{ctx.automation_run_data.project_id}**."
        fields = [
            {"name": "Model", "value": f"`{ctx.automation_run_data.triggers[0].payload.model_id}`", "inline": True},
            {"name": "Failed Elements", "value": str(len(penetration_errors)), "inline": True},
            {"name": "🤖 Site Manager's Advice", "value": ai_suggestion, "inline": False},
        ]
        send_webhook_notification(ctx, title, description, 15158332, fields)

        ctx.attach_error_to_objects(
            category="Unsealed Fire Penetration",
            affected_objects=penetration_errors,
            message=f"This opening requires a fire seal ('{FIRE_SEAL_PARAM}' parameter must be 'Si')."
        )
    
    print(f"Rule #3 Finished. {len(penetration_errors)} errors found.", flush=True)
    return penetration_errors

def run_budget_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Nuova Regola #4: Controlla se il costo totale per categoria sfora il budget.
    """
    print("--- RUNNING RULE #4: BUDGET SANITY CHECK ---", flush=True)
    
    costs_by_category = {}
    for el in all_elements:
        category = getattr(el, 'category', '')
        # Consideriamo solo le categorie per cui abbiamo definito un budget
        if category in BUDGETS:
            try:
                properties = getattr(el, 'properties', {})
                revit_parameters = properties.get('Parameters', {})
                instance_params = revit_parameters.get('Instance Parameters', {})
                text_group = instance_params.get(PARAMETER_GROUP, {})
                cost_param = text_group.get(COST_PARAMETER, {})
                unit_cost = cost_param.get("value", 0)
                volume = getattr(el, 'volume', 0) # Assumiamo costo al m³
                
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
            print(f"BUDGET ALERT: Category '{category}' is over budget by €{overrun:.2f}", flush=True)
            # Aggiungiamo l'oggetto intero alla lista degli errori per poterlo segnalare
            budget_alerts.append(
                {
                    "message": f"Category '{category}' is over budget by €{overrun:.2f} (Total: €{total_cost:.2f}, Budget: €{budget:.2f})",
                    "elements": [el for el in all_elements if getattr(el, 'category', '') == category]
                }
            )

    if budget_alerts:
        # Per la notifica, usiamo il primo sforamento trovato
        first_alert = budget_alerts[0]
        error_description = first_alert["message"]
        
        ai_prompt = (
            "Agisci come un esperto di controllo costi di progetto. "
            "Dato il seguente sforamento di budget rilevato in un modello BIM, "
            "fornisci due azioni correttive concrete per il Project Manager. "
            "Sii conciso e usa un formato markdown (lista puntata). "
            f"Problema: '{error_description}'."
        )
        ai_suggestion = get_ai_suggestion(ai_prompt)

        title = "🚨 Validation Alert: Budget Overrun"
        description = f"A budget check failed in project **{ctx.automation_run_data.project_id}**."
        fields = [
            {"name": "Model", "value": f"`{ctx.automation_run_data.triggers[0].payload.model_id}`", "inline": True},
            {"name": "Issue", "value": error_description, "inline": False},
            {"name": "🤖 Cost Manager's Advice", "value": ai_suggestion, "inline": False},
        ]
        send_webhook_notification(ctx, title, description, 16776960, fields) # Giallo per avviso

        # Alleghiamo un avviso a tutti gli elementi della categoria che ha sforato
        ctx.attach_warning_to_objects(
            category="Budget Overrun",
            affected_objects=first_alert["elements"],
            message=first_alert["message"],
        )
        return ["Budget overrun detected"] # Restituisce un errore per far fallire la Run
    
    print(f"Rule #4 Finished. {len(budget_alerts)} budget issues found.", flush=True)
    return []


#============== ORCHESTRATORE PRINCIPALE =============================================
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

        all_errors = []
        all_errors.extend(run_fire_rating_check(all_elements, ctx))
        all_errors.extend(run_penetration_check(all_elements, ctx))
        all_errors.extend(run_budget_check(all_elements, ctx))
        
        all_errors = [e for e in all_errors if e]

        if all_errors:
            ctx.mark_run_failed(f"Validation failed with a total of {len(all_errors)} issues.")
        else:
            ctx.mark_run_success("Validation passed: All rules were successful.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- VALIDATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
