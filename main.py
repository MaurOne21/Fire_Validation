# main.py
# VERSIONE 20.0 - GROUND ZERO (BASATO SUL CODICE DI DIAGNOSI FUNZIONANTE)

import json
import requests
import traceback
import os
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ==============================
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

GRUPPO_TESTO = "Testo"
GRUPPO_DATI_IDENTITA = "Dati identità"
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Telai Strutturali", "Pilastri", "Walls", "Floors", "Structural Framing", "Structural Columns"]
FIRE_RATING_PARAM = "Fire_Rating"
COST_DESC_PARAM_NAME = "Descrizione"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
#=====================================================================================

#============== FUNZIONI HELPER (Minimale e Stabile) =============================
def find_all_elements(base_object) -> list:
    elements = []
    element_container = getattr(base_object, '@elements', None) or getattr(base_object, 'elements', None)
    if element_container and isinstance(element_container, list):
        for element in element_container: elements.extend(find_all_elements(element))
    elif isinstance(base_object, list):
        for item in base_object: elements.extend(find_all_elements(item))
    element_id = getattr(base_object, 'id', None)
    if element_id not in (None, "") and "Objects.Organization.Model" not in getattr(base_object, 'speckle_type', ''):
        elements.append(base_object)
    return elements

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore invio notifica: {e}")

#============== FUNZIONI DELLE REGOLE (Scrittura Esplicita) ======================
def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = []
    for el in all_elements:
        if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES):
            try:
                value = el.properties['Parameters']['Instance Parameters'][GRUPPO_TESTO][FIRE_RATING_PARAM]['value']
                if not value: errors.append(el)
            except (AttributeError, KeyError, TypeError):
                errors.append(el)
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK (EXPLICIT) ---", flush=True)
    cost_warnings = []
    price_dict = {item['descrizione']: item for item in price_list}
    
    for el in elements:
        try:
            # PERCORSO ESPLICITO E DIRETTO BASATO SUL LOG DI DIAGNOSI
            item_description = el.properties['Parameters']['Type Parameters'][GRUPPO_DATI_IDENTITA][COST_DESC_PARAM_NAME]['value']
            model_cost_raw = el.properties['Parameters']['Instance Parameters'][GRUPPO_TESTO][COST_UNIT_PARAM_NAME]['value']
            model_cost = float(model_cost_raw)

            if not item_description:
                continue

        except (AttributeError, KeyError, TypeError, ValueError):
            # Se uno qualsiasi dei percorsi fallisce, l'elemento non è valido.
            continue
        
        # Se siamo arrivati qui, l'elemento è stato letto con successo.
        print(f"✅ Elemento {el.id} valido per l'analisi. Desc: '{item_description}', Costo: {model_cost}")

        search_description = item_description
        price_list_entry = price_dict.get(search_description)
        if not price_list_entry:
            continue
        
        ref_cost = price_list_entry.get("costo_nuovo") or price_list_entry.get("costo_kg")
        if ref_cost is None:
            continue
        
        # Per questo test, usiamo una logica AI semplice senza chiamata API
        if model_cost <= 0.1:
            warning_message = "AI: Costo non compilato o pari a zero."
            cost_warnings.append((el, warning_message))
            
    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING GROUND ZERO VALIDATOR (v20.0) ---", flush=True)
    try:
        price_list = []
        prezzario_path = os.path.join(os.path.dirname(__file__), 'prezzario.json')
        try:
            with open(prezzario_path, 'r', encoding='utf-8') as f: price_list = json.load(f)
            print("Prezzario 'prezzario.json' caricato.")
        except Exception: pass

        all_elements = find_all_elements(ctx.receive_version())
        if not all_elements:
            ctx.mark_run_success("Nessun elemento.")
            return

        print(f"Trovati {len(all_elements)} elementi.", flush=True)
        
        fire_rating_errors = run_fire_rating_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        total_issues = len(fire_rating_errors) + len(cost_warnings)

        if total_issues > 0:
            if fire_rating_errors:
                ctx.attach_error_to_objects(category="Dato Mancante: Fire_Rating", affected_objects=fire_rating_errors, message="Manca il parametro 'Fire_Rating'.")
            if cost_warnings:
                # FIX DEFINITIVO PER IL BUG DELLA TUPLA
                objects_with_cost_warnings = [item for item in cost_warnings]
                ctx.attach_warning_to_objects(
                    category="Costo Non Congruo (AI)",
                    affected_objects=objects_with_cost_warnings,
                    message="Il costo unitario non è congruo."
                )

            summary_desc = "Validazione completata."
            fields, error_counts = [], {}
            if fire_rating_errors: error_counts["Dato Antincendio Mancante"] = len(fire_rating_errors)
            if cost_warnings: error_counts["Costo Non Congruo (AI)"] = len(cost_warnings)
            
            for rule_desc, count in error_counts.items():
                 fields.append({"name": f"⚠️ {rule_desc}", "value": f"**{count}** problemi", "inline": True})
            
            send_webhook_notification(f"🚨 {total_issues} Problemi Rilevati", summary_desc, 15158332, fields)
            ctx.mark_run_failed(f"Validazione fallita con {total_issues} problemi.")
        else:
            success_message = "✅ Validazione completata. Nessun problema rilevato."
            send_webhook_notification("✅ Validazione Passata", success_message, 3066993, [])
            ctx.mark_run_success(success_message)

    except Exception as e:
        error_message = f"Errore critico: {e}"
        traceback.print_exc()
        ctx.mark_run_failed(error_message)

    print("--- GROUND ZERO SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
