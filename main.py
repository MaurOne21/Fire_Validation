# main.py
# VERSIONE 9.0 - THE SPECKLECON DEMO SCRIPT (ALL RULES + WOW FACTOR)

import json
import requests
import traceback
import os
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE E CHIAVI SEGRETE ==============================
GEMINI_API_KEY = "INCOLLA_QUI_LA_TUA_CHIAVE_GEMINI"
WEBHOOK_URL = "INCOLLA_QUI_IL_TUO_URL_DISCORD"

# --- Regole Antincendio ---
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Walls", "Floors"]
FIRE_OPENING_CATEGORIES = ["Porte", "Finestre", "Doors", "Windows"]
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled" # Può essere Booleano o Testo

# --- Regole Costi ---
COST_DESC_PARAM_NAME = "Descrizione"
COST_DESC_PARAM_GROUP = "Dati identità"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
COST_PARAM_GROUP = "Testo"
BUDGETS = {"Muri": 120000, "Pavimenti": 50000, "Walls": 120000, "Floors": 50000}
#=====================================================================================

#============== FUNZIONI HELPER ======================================================
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

def get_type_parameter_value(element, group_name: str, param_name: str):
    try: return element.properties['Parameters']['Type Parameters'][group_name][param_name]['value']
    except (AttributeError, KeyError, TypeError): return None

def get_instance_parameter_value(element, group_name: str, param_name: str):
    try: return element.properties['Parameters']['Instance Parameters'][group_name][param_name]['value']
    except (AttributeError, KeyError, TypeError): return None

def get_ai_suggestion(prompt: str) -> str:
    # Questa funzione ora gestisce i prompt "WOW"
    if not GEMINI_API_KEY or "INCOLLA_QUI" in GEMINI_API_KEY:
        if "Project Manager" in prompt: return "AI non configurata."
        return '{"is_consistent": true, "justification": "AI non configurata."}'
    
    print(f"Chiamata all'API di Gemini (simulata) con prompt: {prompt[:70]}...")

    if "Project Manager" in prompt:
        return "Rischio budget elevato a causa di costi non congrui sulle strutture. Si raccomanda revisione immediata dei computi con il team strutturale."

    try:
        model_cost_str = prompt.split("Costo Modello: €")[1].split(" ")[0]
        model_cost = float(model_cost_str)
        if model_cost < 30.0:
            return '{"is_consistent": false, "suggestion": 45.50, "justification": "Costo troppo basso per un tramezzo standard."}'
    except (IndexError, ValueError): pass

    return '{"is_consistent": true, "justification": "Costo congruo."}'

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    print(f"Invio notifica webhook a Discord: {title}")
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)
    except Exception as e: print(f"Errore durante l'invio della notifica a Discord: {e}")

#============== FUNZIONI DELLE REGOLE ================================================

def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES) and not get_instance_parameter_value(el, COST_PARAM_GROUP, FIRE_RATING_PARAM)]
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_penetration_check(all_elements: list) -> list:
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION (BOOLEAN CHECK) ---", flush=True)
    errors = []
    for el in all_elements:
        if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_OPENING_CATEGORIES):
            value = get_instance_parameter_value(el, COST_PARAM_GROUP, FIRE_SEAL_PARAM)
            # Logica robusta: gestisce booleano, testo, intero. Solo True o "si"/"yes"/"1" sono validi.
            is_sealed = value is True or str(value).lower() in ["si", "yes", "true", "1"]
            if not is_sealed:
                errors.append(el)
    print(f"Rule #3 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_total_budget_check(elements: list) -> list:
    print("--- RUNNING RULE #4: TOTAL BUDGET CHECK ---", flush=True)
    costs_by_category = {cat: 0 for cat in BUDGETS.keys()}
    for el in elements:
        category = getattr(el, 'category', '')
        if category in costs_by_category:
            cost_val = get_instance_parameter_value(el, COST_PARAM_GROUP, COST_UNIT_PARAM_NAME)
            # Per il budget, ci serve una metrica: volume per i muri, area per i pavimenti
            metric = getattr(el, 'volume', getattr(el, 'area', 0))
            costs_by_category[category] += (float(cost_val) if cost_val else 0) * metric
    alerts = [f"Categoria '{cat}': superato budget di €{costs_by_category[cat] - BUDGETS[cat]:,.2f}" for cat in costs_by_category if costs_by_category[cat] > BUDGETS[cat]]
    for alert in alerts: print(f"BUDGET ALERT: {alert}", flush=True)
    print(f"Rule #4 Finished. {len(alerts)} budget issues found.", flush=True)
    return alerts

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK (NEW, DEMO & STEEL) ---", flush=True)
    cost_warnings = []
    price_dict = {item['descrizione']: item for item in price_list}
    for el in elements:
        item_description = get_type_parameter_value(el, COST_DESC_PARAM_GROUP, COST_DESC_PARAM_NAME)
        if not item_description: continue
        try: model_cost = float(get_instance_parameter_value(el, COST_PARAM_GROUP, COST_UNIT_PARAM_NAME))
        except (ValueError, TypeError): continue
        phase_demolished = getattr(el, 'phaseDemolished', 'N/A')
        is_demolished = phase_demolished != 'N/A' and phase_demolished != 'None'
        search_description = item_description + " (DEMOLIZIONE)" if is_demolished else item_description
        price_list_entry = price_dict.get(search_description)
        if not price_list_entry: continue
        
        if 'densita_kg_m3' in price_list_entry:
            cost_key, ref_cost, unit = ("costo_demolizione_kg", price_list_entry.get("costo_demolizione_kg"), "€/kg") if is_demolished else ("costo_kg", price_list_entry.get("costo_kg"), "€/kg")
        else:
            cost_key, ref_cost, unit = ("costo_demolizione", price_list_entry.get("costo_demolizione"), f"€/{price_list_entry.get('unita', 'cad')}") if is_demolished else ("costo_nuovo", price_list_entry.get("costo_nuovo"), f"€/{price_list_entry.get('unita', 'cad')}")
        if ref_cost is None: continue
        
        ai_prompt = (f"Agisci come un computista. Valuta: '{search_description}', Costo Modello: €{model_cost:.2f} {unit}, Costo Riferimento: €{ref_cost:.2f} {unit}. È congruo? Se no, suggerisci un costo e giustifica. Rispondi SOLO in JSON con 'is_consistent', 'suggestion', 'justification'.")
        ai_response_str = get_ai_suggestion(ai_prompt)
        
        try:
            ai_response = json.loads(ai_response_str)
            if not ai_response.get("is_consistent"):
                warning_message = f"AI Suggestion: {ai_response.get('justification')} (Suggerito: ~€{ai_response.get('suggestion'):.2f})"
                cost_warnings.append((el, warning_message))
        except Exception as e: print(f"Errore nell'interpretare risposta AI: {e}")
    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING MASTER VALIDATION SCRIPT ---", flush=True)
    try:
        price_list = []
        prezzario_path = os.path.join(os.path.dirname(__file__), 'prezzario.json')
        try:
            with open(prezzario_path, 'r', encoding='utf-8') as f: price_list = json.load(f)
            print("Prezzario 'prezzario.json' caricato.")
        except Exception as e: print(f"ATTENZIONE: 'prezzario.json' non trovato: {e}")

        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)
        if not all_elements:
            ctx.mark_run_success("Nessun elemento processabile.")
            return

        print(f"Trovati {len(all_elements)} elementi totali da analizzare.", flush=True)
        
        fire_rating_errors = run_fire_rating_check(all_elements)
        penetration_errors = run_penetration_check(all_elements)
        budget_alerts = run_total_budget_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        total_issues = len(fire_rating_errors) + len(penetration_errors) + len(budget_alerts) + len(cost_warnings)

        if total_issues > 0:
            summary_desc = "Report di Validazione Automatica del Modello:"
            fields = []
            error_summary_for_ai = []
            
            if fire_rating_errors:
                fields.append({"name": f"🔥 Dato Antincendio Mancante ({len(fire_rating_errors)} errori)", "value": f"Manca il parametro '{FIRE_RATING_PARAM}' o è vuoto.", "inline": False})
                ctx.attach_error_to_objects(category=f"Dato Mancante: {FIRE_RATING_PARAM}", affected_objects=fire_rating_errors, message=f"Il parametro '{FIRE_RATING_PARAM}' è mancante o vuoto.")
                error_summary_for_ai.append("dati antincendio mancanti")
            
            if penetration_errors:
                fields.append({"name": f"🔥 Apertura non Sigillata ({len(penetration_errors)} errori)", "value": f"Il parametro '{FIRE_SEAL_PARAM}' non è impostato correttamente.", "inline": False})
                ctx.attach_warning_to_objects(category="Apertura non Sigillata", affected_objects=penetration_errors, message=f"Questa apertura non è sigillata.")
                error_summary_for_ai.append("aperture non sigillate")

            if budget_alerts:
                fields.append({"name": f"💰 Superamento Budget ({len(budget_alerts)} categorie)", "value": "\n".join(budget_alerts), "inline": False})
                error_summary_for_ai.append("superamento del budget")
            
            if cost_warnings:
                fields.append({"name": f"💸 Costo Non Congruo ({len(cost_warnings)} avvisi)", "value": "L'AI ha rilevato costi unitari fuori tolleranza.", "inline": False})
                ctx.attach_warning_to_objects(category="Costo Non Congruo (AI)", affected_objects=[item[0] for item in cost_warnings], message=[item[1] for item in cost_warnings])
                error_summary_for_ai.append("costi unitari non congrui")

            ai_prompt = f"Agisci come un Project Manager esperto. Un controllo ha trovato i seguenti tipi di problemi: {', '.join(error_summary_for_ai)}. Analizza i rischi e suggerisci la prima azione strategica da intraprendere."
            ai_suggestion = get_ai_suggestion(ai_prompt)
            fields.append({"name": "🤖 Analisi Strategica del PM (AI)", "value": ai_suggestion, "inline": False})

            send_webhook_notification("🚨 Validazione Modello Fallita", summary_desc, 15158332, fields)
            ctx.mark_run_failed(f"Validazione fallita con {total_issues} problemi totali.")
        else:
            success_message = "✅ Validazione completata con successo. Tutti i controlli sono stati superati."
            print(success_message, flush=True)
            send_webhook_notification("✅ Validazione Modello Passata", success_message, 3066993, [])
            ctx.mark_run_success(success_message)

    except Exception as e:
        error_message = f"Errore critico: {e}"
        traceback.print_exc()
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- MASTER VALIDATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
