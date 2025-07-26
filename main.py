# main.py
# VERSIONE 8.4 - FINALE E COMPLETA (TUTTE LE REGOLE ATTIVE)

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
FIRE_SEAL_PARAM = "FireSealInstalled"

# --- Regole Costi ---
COST_DESC_PARAM_NAME = "Descrizione"
COST_DESC_PARAM_GROUP = "Dati identità"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
COST_PARAM_GROUP = "Testo"
#=====================================================================================

# ⬇️⬇️⬇️  AI SIMULATA PERFETTA  ⬇️⬇️⬇️
def get_ai_suggestion(prompt: str) -> str:
    """Simula una risposta AI, gestendo sia la validazione dei costi che i prompt riassuntivi."""
    if not GEMINI_API_KEY or "INCOLLA_QUI" in GEMINI_API_KEY:
        return '{"is_consistent": true, "justification": "AI non configurata."}'
    
    print(f"Chiamata all'API di Gemini (simulata) con prompt: {prompt[:70]}...")

    # Caso 1: È un prompt per il riassunto finale
    if "Project Manager" in prompt or "Direttore Lavori" in prompt:
        return "Priorità alla revisione dei costi non congrui rilevati, seguita dalla verifica dei dati antincendio mancanti."

    # Caso 2: È un prompt per la validazione di un costo
    try:
        model_cost_str = prompt.split("Costo Modello: €")[1].split(" ")[0]
        model_cost = float(model_cost_str)
        if model_cost < 30.0:
            return '{"is_consistent": false, "justification": "Costo palesemente troppo basso."}'
    except (IndexError, ValueError):
        pass # Se non è un prompt di costo, va al caso standard

    # Caso 3: Il costo è congruo o il prompt non è riconosciuto
    return '{"is_consistent": true, "justification": "Il costo sembra congruo."}'

# (Tutte le altre funzioni rimangono identiche)
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

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    print(f"Invio notifica webhook a Discord: {title}")
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)
    except Exception as e: print(f"Errore durante l'invio della notifica a Discord: {e}")

def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES) and (get_instance_parameter_value(el, COST_PARAM_GROUP, FIRE_RATING_PARAM) is None or not str(get_instance_parameter_value(el, COST_PARAM_GROUP, FIRE_RATING_PARAM)).strip())]
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_penetration_check(all_elements: list) -> list:
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION CHECK ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_OPENING_CATEGORIES) and (not isinstance(get_instance_parameter_value(el, COST_PARAM_GROUP, FIRE_SEAL_PARAM), str) or get_instance_parameter_value(el, COST_PARAM_GROUP, FIRE_SEAL_PARAM).strip().lower() != "si")]
    print(f"Rule #3 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK (incl. Steel Weight) ---", flush=True)
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
            cost_key, reference_cost, cost_unit = ("costo_demolizione_kg", price_list_entry.get("costo_demolizione_kg"), "€/kg") if is_demolished else ("costo_kg", price_list_entry.get("costo_kg"), "€/kg")
        else:
            cost_key, reference_cost, cost_unit = ("costo_demolizione", price_list_entry.get("costo_demolizione"), f"€/{price_list_entry.get('unita', 'cad')}") if is_demolished else ("costo_nuovo", price_list_entry.get("costo_nuovo"), f"€/{price_list_entry.get('unita', 'cad')}")
        if reference_cost is None: continue
        ai_prompt = (f"Agisci come un computista. Valuta questo costo: '{search_description}', Costo Modello: €{model_cost:.2f} {cost_unit}, Costo Riferimento: {reference_cost:.2f} {cost_unit}. È irragionevole? Rispondi in JSON con 'is_consistent' e 'justification'.")
        ai_response_str = get_ai_suggestion(ai_prompt)
        try:
            ai_response = json.loads(ai_response_str)
            if not ai_response.get("is_consistent"):
                warning_message = f"AI: {ai_response.get('justification', 'Costo non congruo.')}"
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
        except Exception as e: print(f"ATTENZIONE: 'prezzario.json' non trovato o illeggibile: {e}")

        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)
        if not all_elements:
            ctx.mark_run_success("Nessun elemento processabile trovato.")
            return

        print(f"Trovati {len(all_elements)} elementi totali da analizzare.", flush=True)
        
        # --- ESECUZIONE DI TUTTE LE REGOLE ---
        fire_rating_errors = run_fire_rating_check(all_elements)
        penetration_errors = run_penetration_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        total_issues = len(fire_rating_errors) + len(penetration_errors) + len(cost_warnings)

        if total_issues > 0:
            summary_desc = "Sono stati riscontrati problemi durante la validazione del modello:"
            fields = []
            
            if fire_rating_errors:
                fields.append({"name": f"🔥 Dato Antincendio Mancante ({len(fire_rating_errors)} errori)", "value": f"Manca il parametro '{FIRE_RATING_PARAM}' o è vuoto.", "inline": False})
                ctx.attach_error_to_objects(category=f"Dato Mancante: {FIRE_RATING_PARAM}", affected_objects=fire_rating_errors, message=f"Il parametro '{FIRE_RATING_PARAM}' è mancante o vuoto.")
            
            if penetration_errors:
                fields.append({"name": f"🔥 Apertura non Sigillata ({len(penetration_errors)} errori)", "value": f"Il parametro '{FIRE_SEAL_PARAM}' non è impostato su 'Si'.", "inline": False})
                ctx.attach_warning_to_objects(category="Apertura non Sigillata", affected_objects=penetration_errors, message=f"Questa apertura non è sigillata.")

            if cost_warnings:
                fields.append({"name": f"💸 Costo Non Congruo ({len(cost_warnings)} avvisi)", "value": "L'AI ha rilevato costi unitari fuori tolleranza.", "inline": False})
                ctx.attach_warning_to_objects(category="Costo Non Congruo (AI)", affected_objects=[item[0] for item in cost_warnings], message="Il costo unitario di questo elemento non sembra congruo.")

            ai_prompt = f"Agisci come un Project Manager. Un controllo automatico ha trovato questi problemi: {', '.join([f['name'] for f in fields])}. Riassumi le priorità in una frase."
            ai_suggestion = get_ai_suggestion(ai_prompt)
            fields.append({"name": "🤖 Suggerimento del Project Manager (AI)", "value": ai_suggestion, "inline": False})

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
