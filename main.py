# main.py
# VERSIONE 13.4 - CON DEBUG DIAGNOSTICO PER I COSTI

import json
import requests
import traceback
import os
from speckle_automate import AutomationContext, execute_automate_function

# (Tutta la configurazione e le funzioni helper fino a run_ai_cost_check rimangono identiche)
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"
GRUPPO_TESTO = "Testo"
GRUPPO_DATI_IDENTITA = "Dati identità"
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Telai Strutturali", "Pilastri", "Walls", "Floors", "Structural Framing", "Structural Columns"]
FIRE_OPENING_CATEGORIES = ["Porte", "Finestre", "Doors", "Windows"]
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"
COST_DESC_PARAM_NAME = "Descrizione"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
BUDGETS = {"Muri": 120000, "Pavimenti": 50000, "Walls": 120000, "Floors": 50000}

def find_all_elements(base_object) -> list:
    # ...
    elements = []
    element_container = getattr(base_object, '@elements', None) or getattr(base_object, 'elements', None)
    if element_container and isinstance(element_container, list):
        for element in element_container: elements.extend(find_all_elements(element))
    elif isinstance(base_object, list):
        for item in base_object: elements.extend(find_all_elements(item))
    if getattr(base_object, 'id', None) is not None and "Objects.Organization.Model" not in getattr(base_object, 'speckle_type', ''):
        elements.append(base_object)
    return elements

def get_type_parameter_value(element, group_name: str, param_name: str):
    try: return element.properties['Parameters']['Type Parameters'][group_name][param_name]['value']
    except (AttributeError, KeyError, TypeError): return None

def get_instance_parameter_value(element, group_name: str, param_name: str):
    try: return element.properties['Parameters']['Instance Parameters'][group_name][param_name]['value']
    except (AttributeError, KeyError, TypeError): return None

def get_ai_suggestion(prompt: str) -> str:
    if not GEMINI_API_KEY or "INCOLLA_QUI" in GEMINI_API_KEY:
        if "Riassumi le priorità" in prompt: return "AI non configurata."
        return '{"is_consistent": true, "justification": "AI non configurata."}'
    print(f"Chiamata all'API di Gemini (simulata)...")
    
    if "Riassumi le priorità" in prompt:
        return "Priorità alla revisione dei dati antincendio mancanti e dei costi non congrui."
    try:
        model_cost_str = prompt.split("Costo Modello: €")[1].split(" ")[0]
        model_cost = float(model_cost_str)
        # Un costo a zero (o molto basso) è quasi sempre un errore
        if model_cost <= 0.1: 
            return '{"is_consistent": false, "suggestion": 45.50, "justification": "Costo unitario non compilato o pari a zero."}'
        if model_cost < 30.0:
            return '{"is_consistent": false, "suggestion": 45.50, "justification": "Costo palesemente troppo basso."}'
    except (IndexError, ValueError):
        pass
    return '{"is_consistent": true, "justification": "Costo congruo."}'

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    # ...
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    print(f"Invio notifica webhook a Discord: {title}")
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore durante l'invio della notifica a Discord: {e}")

def run_fire_rating_check(all_elements: list) -> list:
    # ...
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES) and not get_instance_parameter_value(el, GRUPPO_TESTO, FIRE_RATING_PARAM)]
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_penetration_check(all_elements: list) -> list:
    # ...
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION ---", flush=True)
    errors = []
    for el in all_elements:
        if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_OPENING_CATEGORIES):
            value = get_instance_parameter_value(el, GRUPPO_TESTO, FIRE_SEAL_PARAM)
            if not (value is True or str(value).lower() in ["si", "yes", "true", "1"]):
                errors.append(el)
    print(f"Rule #3 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_total_budget_check(elements: list) -> list:
    # ...
    print("--- RUNNING RULE #4: TOTAL BUDGET CHECK ---", flush=True)
    costs_by_category = {cat: 0 for cat in BUDGETS.keys()}
    for el in elements:
        category = getattr(el, 'category', '')
        if category in costs_by_category:
            cost_val = get_instance_parameter_value(el, GRUPPO_TESTO, COST_UNIT_PARAM_NAME)
            metric = getattr(el, 'volume', getattr(el, 'area', 0))
            costs_by_category[category] += (float(cost_val) if cost_val else 0) * metric
    alerts = [f"Categoria '{cat}': superato budget di €{costs_by_category[cat] - BUDGETS[cat]:,.2f}" for cat in costs_by_category if costs_by_category[cat] > BUDGETS[cat]]
    print(f"Rule #4 Finished. {len(alerts)} budget issues found.", flush=True)
    return alerts

# ⬇️⬇️⬇️  MODIFICA CHIAVE: DEBUG IPER-DETTAGLIATO  ⬇️⬇️⬇️
def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK ---", flush=True)
    cost_warnings = []
    price_dict = {item['descrizione']: item for item in price_list}
    
    for el in elements:
        # --- BLOCCO DI DEBUG OPZIONALE ---
        # Per riattivare il debug, rimuovi i tre # dalle 6 righe seguenti
        # print(f"\n[DEBUG COST] Ispezione elemento ID: {el.id}, Categoria: {getattr(el, 'category', 'N/A')}")
        # item_description_debug = get_type_parameter_value(el, GRUPPO_DATI_IDENTITA, COST_DESC_PARAM_NAME)
        # cost_value_raw_debug = get_instance_parameter_value(el, GRUPPO_TESTO, COST_UNIT_PARAM_NAME)
        # print(f"  > `Descrizione` (da Tipo): '{item_description_debug}'")
        # print(f"  > `Costo_Unitario` (da Istanza): '{cost_value_raw_debug}'")
        # if item_description_debug and price_dict.get(item_description_debug): print("  > ✅ Match Trovato nel Prezzario")
        
        item_description = get_type_parameter_value(el, GRUPPO_DATI_IDENTITA, COST_DESC_PARAM_NAME)
        if not item_description: continue
        try:
            model_cost = float(get_instance_parameter_value(el, GRUPPO_TESTO, COST_UNIT_PARAM_NAME))
        except (ValueError, TypeError): continue
                #print(f"  > 🔴 MOTIVO SCARTO: 'Costo_Unitario' non è un numero valido.")

            search_description = item_description
            price_list_entry = price_dict.get(search_description)
            if not price_list_entry:
                 # Proviamo a vedere se è un elemento da demolire
                 search_description_demo = item_description + " (DEMOLIZIONE)"
                 price_list_entry = price_dict.get(search_description_demo)
                 if not price_list_entry:
                    print(f"  > 🔴 MOTIVO SCARTO: La descrizione '{search_description}' non corrisponde a nessuna voce nel prezzario.json.")
                    continue
            
            print("  > ✅ CORRISPONDENZA TROVATA! Elemento valido per l'analisi AI.")
        # --- FINE BLOCCO DI DEBUG ---
        else:
            # Se entrambi i parametri sono vuoti, non ci interessa e andiamo avanti in silenzio
            continue


        # (La logica di validazione vera e propria parte solo per gli elementi che superano i controlli)
        phase_demolished = getattr(el, 'phaseDemolished', 'N/A')
        is_demolished = phase_demolished != 'N/A' and phase_demolished != 'None'
        search_description = item_description + " (DEMOLIZIONE)" if is_demolished else item_description
        price_list_entry = price_dict.get(search_description)
        
        if 'densita_kg_m3' in price_list_entry: _, ref_cost, _ = ("costo_demolizione_kg", price_list_entry.get("costo_demolizione_kg"), "€/kg") if is_demolished else ("costo_kg", price_list_entry.get("costo_kg"), "€/kg")
        else: _, ref_cost, _ = ("costo_demolizione", price_list_entry.get("costo_demolizione"), f"€/{price_list_entry.get('unita', 'cad')}") if is_demolished else ("costo_nuovo", price_list_entry.get("costo_nuovo"), f"€/{price_list_entry.get('unita', 'cad')}")
        if ref_cost is None: continue
        
        ai_prompt = (f"Valuta: '{search_description}', Costo Modello: €{model_cost:.2f}, Riferimento: €{ref_cost:.2f}")
        ai_response_str = get_ai_suggestion(ai_prompt)
        
        try:
            ai_response = json.loads(ai_response_str)
            if not ai_response.get("is_consistent"):
                warning_message = f"AI: {ai_response.get('justification')} (Suggerito: ~€{ai_response.get('suggestion'):.2f})"
                cost_warnings.append((el, warning_message))
        except Exception as e: print(f"Errore interpretazione AI: {e}")

    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings


#============== ORCHESTRATORE PRINCIPALE (GOLDEN MASTER) =======================
def main(ctx: AutomationContext) -> None:
    # ... (Il resto del main è identico alla v13.3)
    print("--- STARTING GOLDEN MASTER VALIDATOR (v13.4 DEBUG) ---", flush=True)
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
        penetration_errors = run_penetration_check(all_elements)
        budget_alerts = run_total_budget_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        total_issues = len(fire_rating_errors) + len(penetration_errors) + len(budget_alerts) + len(cost_warnings)

        if total_issues > 0:
            if fire_rating_errors:
                ctx.attach_error_to_objects(category=f"Dato Mancante: {FIRE_RATING_PARAM}", affected_objects=fire_rating_errors, message=f"Il parametro '{FIRE_RATING_PARAM}' è mancante o vuoto.")
            if penetration_errors:
                ctx.attach_warning_to_objects(category="Apertura non Sigillata", affected_objects=penetration_errors, message=f"Questa apertura non è sigillata.")
            if cost_warnings:
                ctx.attach_warning_to_objects(category="Costo Non Congruo (AI)", affected_objects=[item[0] for item in cost_warnings], message=[item[1] for item in cost_warnings])

            summary_desc = "Validazione completata."
            fields, error_counts = [], {}
            if fire_rating_errors: error_counts["Dato Antincendio Mancante"] = len(fire_rating_errors)
            if penetration_errors: error_counts["Apertura non Sigillata"] = len(penetration_errors)
            if budget_alerts: error_counts["Superamento Budget"] = len(budget_alerts)
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

    print("--- GOLDEN MASTER SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
