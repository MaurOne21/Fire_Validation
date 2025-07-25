# main.py
# Versione con integrazione AI per le Regole #1 e #3.

import json
import requests
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
# ❗ INSERISCI QUI LE TUE CHIAVI!
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://webhook.site/7787200c-ab85-499c-9a90-5416a2fbd072"

# --- Regole ---
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti"]
OPENING_CATEGORIES = ["Porte", "Finestre"] 
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"
PARAMETER_GROUP = "Testo"
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


#============== FUNZIONI DI SUPPORTO PER AI E NOTIFICHE (NUOVE!) =======================
def get_ai_suggestion(error_description: str) -> str:
    """
    Interroga l'API di Gemini per ottenere un suggerimento basato sulla descrizione dell'errore.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "LA_TUA_CHIAVE_API_DI_GEMINI":
        return "AI suggestion not available (API key not configured)."

    print("Asking AI for a suggestion...", flush=True)
    prompt = (
        "Sei un BIM Manager esperto e conciso. "
        "Dato il seguente errore di validazione di un modello BIM, "
        "fornisci due brevi azioni correttive in formato markdown (lista puntata). "
        f"Errore: '{error_description}'"
    )
    
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

def send_webhook_notification(ctx: AutomationContext, error_category: str, failed_elements: list, ai_suggestion: str):
    """
    Invia una notifica a un webhook generico con i dettagli dell'errore.
    """
    if not WEBHOOK_URL or WEBHOOK_URL == "IL_TUO_URL_DA_WEBHOOK.SITE":
        return

    print("Sending webhook notification...", flush=True)
    
    commit_url = f"{ctx.speckle_client.url}/projects/{ctx.automation_run_data.project_id}/models/{ctx.automation_run_data.model_id}@{ctx.automation_run_data.version_id}"
    
    # Messaggio JSON semplice, perfetto per Webhook.site
    message = {
        "alert_type": "Speckle Automation Alert",
        "error_category": error_category,
        "project_id": ctx.automation_run_data.project_id,
        "model_id": ctx.automation_run_data.model_id,
        "failed_elements_count": len(failed_elements),
        "ai_suggestion": ai_suggestion,
        "link_to_commit": commit_url
    }

    try:
        requests.post(WEBHOOK_URL, json=message)
    except Exception as e:
        print(f"Could not send webhook notification. Reason: {e}", flush=True)


#============== LOGICA DELLE REGOLE (POTENZIATA) =====================================
def run_fire_rating_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #1: Verifica che tutti i muri e solai abbiano
    il parametro 'Fire_Rating' compilato.
    """
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    
    validation_errors = []
    # ... (la logica di validazione omessa per brevità, ma è la stessa di prima)

    if validation_errors:
        error_description = f"{len(validation_errors)} elements are missing the '{FIRE_RATING_PARAM}' parameter."
        ai_suggestion = get_ai_suggestion(error_description)
        send_webhook_notification(ctx, f"Missing Data: {FIRE_RATING_PARAM}", validation_errors, ai_suggestion)

        ctx.attach_error_to_objects(
            category=f"Missing Data: {FIRE_RATING_PARAM}",
            affected_objects=validation_errors,
            message=f"The parameter '{FIRE_RATING_PARAM}' is missing or empty.",
            visual_overrides={"color": "red"}
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
    # ... (la logica di validazione omessa per brevità, ma è la stessa di prima)

    if penetration_errors:
        error_description = f"{len(penetration_errors)} openings require a fire seal ('{FIRE_SEAL_PARAM}' parameter must be 'Si')."
        ai_suggestion = get_ai_suggestion(error_description)
        send_webhook_notification(ctx, "Unsealed Fire Penetration", penetration_errors, ai_suggestion)

        ctx.attach_error_to_objects(
            category="Unsealed Fire Penetration",
            affected_objects=penetration_errors,
            message=f"This opening requires a fire seal ('{FIRE_SEAL_PARAM}' parameter must be 'Si').",
            visual_overrides={"color": "#FF8C00"}
        )
    
    print(f"Rule #3 Finished. {len(penetration_errors)} errors found.", flush=True)
    return penetration_errors


#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    # ... (logica dell'orchestratore omessa per brevità, ma è la stessa di prima)

if __name__ == "__main__":
    execute_automate_function(main)
