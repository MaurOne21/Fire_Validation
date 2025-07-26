# main.py
# Versione corretta e migliorata

import json
import requests
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
# --- Regole ---
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti", "Walls", "Floors"]
OPENING_CATEGORIES = ["Porte", "Finestre", "Doors", "Windows"]
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"
PARAMETER_GROUP = "Testo"  # Assicurati che il nome del gruppo sia corretto

# --- Regola #4 ---
COST_PARAMETER = "Costo_Unitario"
BUDGETS = {"Pavimenti": 50000, "Muri": 120000, "Floors": 50000, "Walls": 120000}
#=====================================================================================

#============== FUNZIONE DI RICERCA ELEMENTI (CORRETTA) ==============================
def find_all_elements(base_object) -> list:
    """
    Attraversa ricorsivamente l'oggetto commit per trovare tutti gli elementi.
    """
    elements = []
    
    # Cerca un attributo '@elements' o 'elements' che contiene altri oggetti
    element_container = getattr(base_object, '@elements', None) or getattr(base_object, 'elements', None)
    
    if element_container and isinstance(element_container, list):
        for element in element_container:
            elements.extend(find_all_elements(element))

    # Se l'oggetto stesso è una lista (es. un livello che contiene oggetti)
    elif isinstance(base_object, list):
        for item in base_object:
            elements.extend(find_all_elements(item))

    # Consideriamo un oggetto un "elemento" se ha un ID.
    # Questo esclude contenitori logici come "Collection" o "Model"
    if getattr(base_object, 'id', None) is not None:
         # Evita di aggiungere il root object stesso se è solo un contenitore
        if "Objects.Organization.Model" not in getattr(base_object, 'speckle_type', ''):
            elements.append(base_object)
            
    return elements

#============== FUNZIONI DI SUPPORTO (DA IMPLEMENTARE) ================================
def get_ai_suggestion(prompt: str, api_key: str) -> str:
    # Qui andrà la logica per chiamare l'API di Gemini
    # Placeholder per ora
    print("Chiamata AI (simulata).")
    return "Suggerimento AI: Verificare immediatamente le compartimentazioni antincendio e revisionare i costi dei muri."

def send_webhook_notification(ctx: AutomationContext, webhook_url: str, title: str, description: str, color: int, fields: list):
    # Qui andrà la logica per inviare la notifica a Discord/Teams
    # Placeholder per ora
    print(f"Invio notifica webhook (simulata): {title}")
    pass

#============== LOGICA DELLE REGOLE (CON MIGLIORAMENTI DI ROBUSTEZZA) ==================
def get_parameter_value(element, group_name: str, param_name: str):
    """Funzione helper per estrarre in modo sicuro un valore di parametro."""
    try:
        properties = getattr(element, 'properties', {})
        params = properties.get('Parameters', {})
        instance_params = params.get('Instance Parameters', {})
        param_group = instance_params.get(group_name, {})
        param_dict = param_group.get(param_name, {})
        return param_dict.get("value")
    except (AttributeError, KeyError):
        return None

def run_fire_rating_check(all_elements: list) -> list:
    """Esegue la Regola #1. Restituisce una lista di oggetti con errore."""
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
    """Esegue la Regola #3. Restituisce una lista di oggetti con errore."""
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
    """Esegue la Regola #4. Restituisce una lista di messaggi di errore."""
    print("--- RUNNING RULE #4: BUDGET SANITY CHECK ---", flush=True)
    costs_by_category = {}
    
    for category_key in BUDGETS.keys():
        costs_by_category[category_key] = 0

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

# main.py
# Versione completa con fallback per le chiavi API e tutte le correzioni.

import json
import requests
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
# --- Regole ---
# Aggiunte le versioni in inglese per maggiore compatibilità
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti", "Walls", "Floors"]
OPENING_CATEGORIES = ["Porte", "Finestre", "Doors", "Windows"]
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"
PARAMETER_GROUP = "Testo"  # Assicurati che questo sia il nome esatto del gruppo parametri in Revit

# --- Regola #4 ---
COST_PARAMETER = "Costo_Unitario"
# Aggiunte le versioni in inglese per maggiore compatibilità
BUDGETS = {"Pavimenti": 50000, "Muri": 120000, "Floors": 50000, "Walls": 120000}
#=====================================================================================


#============== FUNZIONE DI RICERCA ELEMENTI (CORRETTA) ==============================
def find_all_elements(base_object) -> list:
    """
    Attraversa ricorsivamente l'oggetto commit per trovare tutti gli elementi processabili.
    """
    elements = []
    
    # Cerca un attributo '@elements' o 'elements' che contiene altri oggetti
    element_container = getattr(base_object, '@elements', None) or getattr(base_object, 'elements', None)
    
    if element_container and isinstance(element_container, list):
        for element in element_container:
            elements.extend(find_all_elements(element))

    # Se l'oggetto stesso è una lista (es. un livello che contiene oggetti)
    elif isinstance(base_object, list):
        for item in base_object:
            elements.extend(find_all_elements(item))

    # Consideriamo un oggetto un "elemento" se ha un ID univoco.
    # Questo esclude contenitori logici come "Collection" o "Model".
    if getattr(base_object, 'id', None) is not None:
         # Evita di aggiungere il root object stesso se è solo un contenitore
        if "Objects.Organization.Model" not in getattr(base_object, 'speckle_type', ''):
            elements.append(base_object)
            
    return elements


#============== FUNZIONI DI SUPPORTO (DA IMPLEMENTARE COMPLETAMENTE) ===================
def get_ai_suggestion(prompt: str, api_key: str) -> str:
    """
    Invia un prompt all'API di Gemini e restituisce la risposta.
    ❗ DA IMPLEMENTARE: La logica di chiamata HTTP all'API di Gemini va inserita qui.
    """
    if not api_key or "INCOLLA_QUI" in api_key:
        return "ATTENZIONE: Chiave API di Gemini non configurata."
    
    print("Chiamata all'API di Gemini (simulata)...")
    # Esempio di implementazione (DA ADATTARE)
    # response = requests.post(
    #     f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}",
    #     json={"contents": [{"parts": [{"text": prompt}]}]}
    # )
    # if response.status_code == 200:
    #     return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    # else:
    #     return f"Errore nella chiamata AI: {response.text}"
    return "Suggerimento AI: Verificare immediatamente le compartimentazioni antincendio e revisionare i costi dei muri."

def send_webhook_notification(webhook_url: str, title: str, description: str, color: int, fields: list):
    """
    Invia una notifica a un webhook (es. Discord, Teams).
    ❗ DA IMPLEMENTARE: La logica di chiamata HTTP al webhook va inserita qui.
    """
    if not webhook_url or "INCOLLA_QUI" in webhook_url:
        print("ATTENZIONE: URL del Webhook non configurato.")
        return

    print(f"Invio notifica webhook (simulata): {title}")
    # Esempio di implementazione per Discord (DA ADATTARE)
    # data = {
    #     "embeds": [{
    #         "title": title,
    #         "description": description,
    #         "color": color,
    #         "fields": fields
    #     }]
    # }
    # requests.post(webhook_url, json=data)
    pass


#============== LOGICA DELLE REGOLE (CON MIGLIORAMENTI DI ROBUSTEZZA) ==================
def get_parameter_value(element, group_name: str, param_name: str):
    """Funzione helper per estrarre in modo sicuro un valore di parametro da un elemento Speckle."""
    try:
        # Il percorso esatto può variare leggermente a seconda del connettore (es. Revit, Archicad)
        return element["parameters"][group_name][param_name]["value"]
    except (AttributeError, KeyError, TypeError):
        # Un'alternativa comune è che i parametri siano direttamente sotto 'properties'
        try:
            return element['properties']['Parameters']['Instance Parameters'][group_name][param_name]['value']
        except (AttributeError, KeyError, TypeError):
            return None

def run_fire_rating_check(all_elements: list) -> list:
    """Esegue la Regola #1. Restituisce una lista di oggetti con errore."""
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
    """Esegue la Regola #3. Restituisce una lista di oggetti con errore."""
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
    """Esegue la Regola #4. Restituisce una lista di messaggi di errore."""
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


#============== ORCHESTRATORE PRINCIPALE (CON SOLUZIONE ALTERNATIVA) ==================
def main(ctx: AutomationContext) -> None:
    """Funzione principale che orchestra l'esecuzione di tutte le regole di validazione."""
    print("--- STARTING VALIDATION SCRIPT ---", flush=True)
    
    try:
        # ==============================================================================
        # --- INIZIO SOLUZIONE ALTERNATIVA PER LE CHIAVI ---
        # 
        # ❗ ATTENZIONE: INSERISCI LE TUE CHIAVI QUI SOTTO COME SOLUZIONE TEMPORANEA
        # Questo metodo è insicuro per la produzione. Usare i "Secrets" di Speckle non appena possibile.
        
        FALLBACK_GEMINI_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg" 
        FALLBACK_WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

        gemini_api_key = ctx.get_secret("GEMINI_API_KEY") or FALLBACK_GEMINI_KEY
        webhook_url = ctx.get_secret("DISCORD_WEBHOOK_URL") or FALLBACK_WEBHOOK_URL
        
        if gemini_api_key == FALLBACK_GEMINI_KEY:
            print("AVVISO: Utilizzo della chiave API di riserva (fallback) dal codice. Non sicuro!", flush=True)
        if webhook_url == FALLBACK_WEBHOOK_URL:
            print("AVVISO: Utilizzo dell'URL Webhook di riserva (fallback) dal codice. Non sicuro!", flush=True)
        # --- FINE SOLUZIONE ALTERNATIVA ---
        # ==============================================================================

        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("Validazione completata: Nessun elemento processabile trovato nel commit.")
            return

        print(f"Trovati {len(all_elements)} elementi totali da analizzare.", flush=True)

        # Esecuzione di tutte le regole
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
        import traceback
        traceback.print_exc()
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- VALIDATION SCRIPT FINISHED ---", flush=True)

# Questo blocco permette di testare la funzione localmente, se necessario.
if __name__ == "__main__":
    execute_automate_function(main)
            
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
                "Agisci come un Direttore Lavori esperto di BIM. "
                "Hai eseguito un controllo automatico su un modello e hai trovato i seguenti problemi. "
                "Fornisci un commento conciso e un'azione prioritaria da comunicare al team. "
                f"Problemi Rilevati:\n" + "\n".join([f["name"] for f in fields])
            )
            ai_suggestion = get_ai_suggestion(ai_prompt, gemini_api_key)
            fields.append({"name": "🤖 Suggerimento del Direttore Lavori (AI)", "value": ai_suggestion, "inline": False})

            send_webhook_notification(ctx, webhook_url, "🚨 Validazione Modello Fallita", summary_description, 15158332, fields)
            
            ctx.mark_run_failed(f"Validazione fallita con {total_issues} problemi totali.")
        else:
            success_message = "Validazione completata con successo. Tutti i controlli sono stati superati."
            print(success_message, flush=True)
            ctx.mark_run_success(success_message)

    except Exception as e:
        error_message = f"Errore critico durante l'esecuzione dello script: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- VALIDATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
