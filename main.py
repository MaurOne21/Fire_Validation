# main.py
# Versione multidisciplinare con Regole #1, #3 e la nuova Regola #4 (Analisi di Impatto 5D).

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
    # ... (logica funzionante, omessa per brevità)
    
    print(f"Rule #1 Finished. {len(validation_errors)} errors found.", flush=True)
    return validation_errors

def run_penetration_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #3: Controlla che tutte le porte/finestre abbiano
    la sigillatura specificata.
    """
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION CHECK ---", flush=True)
    
    penetration_errors = []
    # ... (logica funzionante, omessa per brevità)
    
    print(f"Rule #3 Finished. {len(penetration_errors)} errors found.", flush=True)
    return penetration_errors

def run_cost_impact_check(current_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #4: Analisi di Impatto 5D con commento dell'AI.
    """
    print("--- RUNNING RULE #4: 5D COST IMPACT ANALYSIS ---", flush=True)
    
    try:
        previous_version = ctx.get_previous_version()
        if not previous_version:
            print("No previous version found. Skipping cost impact analysis.", flush=True)
            return []
            
        previous_elements = find_all_elements(previous_version)
        
        def calculate_total_cost(elements: list) -> float:
            total_cost = 0
            for el in elements:
                try:
                    properties = getattr(el, 'properties', {})
                    revit_parameters = properties.get('Parameters', {})
                    instance_params = revit_parameters.get('Instance Parameters', {})
                    text_group = instance_params.get(PARAMETER_GROUP, {})
                    cost_param = text_group.get(COST_PARAMETER, {})
                    unit_cost = cost_param.get("value", 0)
                    
                    volume = getattr(el, 'volume', 0) # Assumiamo che il costo sia per volume
                    total_cost += volume * unit_cost
                except (AttributeError, KeyError):
                    continue
            return total_cost

        current_cost = calculate_total_cost(current_elements)
        previous_cost = calculate_total_cost(previous_elements)
        cost_delta = current_cost - previous_cost
        
        print(f"Cost analysis complete. Previous: €{previous_cost:.2f}, Current: €{current_cost:.2f}, Delta: €{cost_delta:.2f}", flush=True)

        if abs(cost_delta) > 0.01: # Invia notifica solo se c'è una variazione
            color = 15158332 if cost_delta > 0 else 32768 # Rosso se aumenta, Verde se diminuisce
            delta_sign = "+" if cost_delta > 0 else ""
            
            # Chiamiamo l'AI per commentare la variazione di costo
            ai_prompt = (
                "Agisci come un Direttore Lavori esperto. Il costo del progetto è appena cambiato. "
                f"Il costo precedente era €{previous_cost:.2f}, quello attuale è €{current_cost:.2f}, "
                f"con una variazione di €{cost_delta:.2f}. "
                "Scrivi un breve commento sull'impatto di questa variazione e suggerisci un'azione di controllo."
            )
            ai_comment = get_ai_suggestion(ai_prompt)

            title = f"💰 Cost Impact Alert: € {delta_sign}{cost_delta:.2f}"
            description = "A design change has impacted the estimated project cost."
            fields = [
                {"name": "Previous Total Cost", "value": f"€ {previous_cost:.2f}", "inline": True},
                {"name": "New Total Cost", "value": f"€ {current_cost:.2f}", "inline": True},
                {"name": "🤖 AI Analysis", "value": ai_comment, "inline": False},
            ]
            send_webhook_notification(ctx, title, description, color, fields)

    except Exception as e:
        print(f"ERROR (Rule 4): Could not run cost impact analysis. Reason: {e}", flush=True)
        return ["Cost analysis failed"] 

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
            ctx.mark_run_success("No elements found in the commit.")
            return

        print(f"Found {len(all_elements)} total elements to analyze.", flush=True)

        all_errors = []
        all_errors.extend(run_fire_rating_check(all_elements, ctx))
        all_errors.extend(run_penetration_check(all_elements, ctx))
        
        all_errors.extend(run_cost_impact_check(all_elements, ctx))
        
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
