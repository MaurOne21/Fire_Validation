# main.py
# VERSIONE 25.1 - REPORTING HTML STABILE (NO PLOTLY)

import json
import requests
import traceback
import os
import csv
from datetime import datetime
from collections import defaultdict
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ==============================
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
#=====================================================================================

# (Funzioni helper e delle regole - nessuna modifica)
def find_all_elements(base_object) -> list:
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
    print(f"Chiamata all'AI (simulata)...")
    if "Riassumi le priorità" in prompt:
        return "Team, focus qui. Il controllo automatico ha rilevato dati mancanti critici per l'antincendio e costi non congrui. Dobbiamo sistemare subito. Azione 1 (Paolo - BIM): Isola gli elementi segnalati in Speckle e correggi i parametri mancanti. Azione 2 (Maria - PM): Verifica perché i costi a zero non sono stati intercettati prima. Dobbiamo migliorare le nostre checklist. Forza, chiudiamo il giro entro un'ora."
    return '{"is_consistent": false, "suggestion": 50.0, "justification": "Costo non compilato o pari a zero."}'

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore invio notifica: {e}")

def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES) and not get_instance_parameter_value(el, GRUPPO_TESTO, FIRE_RATING_PARAM)]
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_penetration_check(all_elements: list) -> list:
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
    print("--- RUNNING RULE #4: TOTAL BUDGET CHECK ---", flush=True)
    costs_by_category = defaultdict(float)
    for el in elements:
        category = getattr(el, 'category', '')
        if category in BUDGETS:
            try:
                cost_val = get_instance_parameter_value(el, GRUPPO_TESTO, COST_UNIT_PARAM_NAME)
                metric = getattr(el, 'volume', getattr(el, 'area', 0))
                costs_by_category[category] += (float(cost_val) if cost_val else 0) * metric
            except (AttributeError, KeyError, TypeError, ValueError): continue
    alerts = [f"Categoria '{cat}': superato budget di €{total_cost - BUDGETS[cat]:,.2f}" for cat, total_cost in costs_by_category.items() if total_cost > BUDGETS[cat]]
    print(f"Rule #4 Finished. {len(alerts)} budget issues found.", flush=True)
    return alerts

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK (SIMULATED) ---", flush=True)
    cost_warnings = []
    price_dict = {item['descrizione']: item for item in price_list}
    for el in elements:
        try:
            item_description = get_type_parameter_value(el, GRUPPO_DATI_IDENTITA, COST_DESC_PARAM_NAME)
            model_cost = float(get_instance_parameter_value(el, GRUPPO_TESTO, COST_UNIT_PARAM_NAME))
            if not item_description or not price_dict.get(item_description): continue
            if model_cost <= 0.1:
                ai_response_str = get_ai_suggestion(f"Costo Modello: €{model_cost}")
                ai_response = json.loads(ai_response_str)
                warning_message = f"AI: {ai_response.get('justification')}"
                cost_warnings.append((el, warning_message))
        except (AttributeError, KeyError, TypeError, ValueError): continue
    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings

#============== FUNZIONI DI REPORTING (STABILI) =================================
def create_html_report(all_errors: list, ctx: AutomationContext) -> str:
    if not all_errors:
        return "<h1>✅ Nessun Errore Rilevato</h1>"

    # Costruiamo il link di base al modello
    base_link = f"{ctx.speckle_server_url}/projects/{ctx.project_id}/models/{ctx.model.id}@{ctx.version_id}"

    # Stili CSS per un look professionale
    styles = """
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #2E86C1; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #dddddd; text-align: left; padding: 8px; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        a { color: #3498DB; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
    """
    
    # Intestazione
    header_html = f"<h1>Report di Validazione</h1><p><b>Commit:</b> {ctx.version_id}</p><p><b>Totale Problemi:</b> {len(all_errors)}</p>"

    # Tabella degli errori
    table_header = "<tr><th>Regola</th><th>Livello</th><th>Categoria</th><th>ID Elemento (Link)</th><th>Messaggio</th></tr>"
    table_rows = ""
    for e in all_errors:
        object_link = f"<a href='{base_link}/objects/{e['element_id']}' target='_blank'>{e['element_id']}</a>"
        table_rows += f"<tr><td>{e['rule_description']}</td><td>{e['error_level']}</td><td>{e['element_category']}</td><td>{object_link}</td><td>{e['message']}</td></tr>"
    
    table_html = f"<h2>Dettaglio Errori</h2><table>{table_header}{table_rows}</table>"

    return f"<html><head><title>Speckle Validation Report</title>{styles}</head><body>{header_html}{table_html}</body></html>"

def create_csv_export(all_errors: list, ctx: AutomationContext, file_path: str):
    if not all_errors: return
    # Usiamo un modo "vecchia scuola" e sicuro per avere il commit ID
    commit_id = ctx.webhook_context.get("versionId", "N/A")
    fieldnames = ["timestamp", "commit_id", "rule_id", "rule_description", "element_id", "element_category", "error_level", "message"]
    with open(file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for error in all_errors:
            row = {"commit_id": commit_id, **error, "timestamp": datetime.utcnow().isoformat()}
            final_row = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(final_row)

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING GOLDEN MASTER (v25.1 with Stable Reporting) ---", flush=True)
    try:
        # ... (logica iniziale identica)
        price_list = []
        prezzario_path = os.path.join(os.path.dirname(__file__), 'prezzario.json')
        try:
            with open(prezzario_path, 'r', encoding='utf-8') as f: price_list = json.load(f)
        except Exception: pass
        all_elements = find_all_elements(ctx.receive_version())
        if not all_elements:
            ctx.mark_run_success("Nessun elemento.")
            return
        print(f"Trovati {len(all_elements)} elementi.", flush=True)
        
        # Esecuzione regole
        fire_rating_errors = run_fire_rating_check(all_elements)
        penetration_errors = run_penetration_check(all_elements)
        budget_alerts = run_total_budget_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        # Aggregazione errori
        all_errors_structured = []
        for el in fire_rating_errors:
            all_errors_structured.append({"rule_id": "FIRE-01", "rule_description": "Dato Antincendio Mancante", "element_id": el.id, "element_category": getattr(el, 'category', 'N/A'), "error_level": "ERROR", "message": f"Manca '{FIRE_RATING_PARAM}'."})
        # ... (aggregazione per le altre regole)
        
        total_issues = len(all_errors_structured)

        # ⬇️⬇️⬇️ NUOVA PARTE: GENERAZIONE E SALVATAGGIO REPORT ⬇️⬇️⬇️
        # Usiamo /tmp come percorso sicuro e compatibile
        temp_dir = "/tmp"
        html_report_path = os.path.join(temp_dir, "validation_report.html")
        csv_export_path = os.path.join(temp_dir, "powerbi_export.csv")
        
        # Per costruire i link, abbiamo bisogno di alcuni dati dal contesto che potrebbero non esistere.
        # Li recuperiamo in modo sicuro.
        webhook_context = ctx.webhook_context or {}
        server_url = webhook_context.get("speckleServerUrl", "N/A")
        project_id = webhook_context.get("projectId", "N/A")
        model_id = webhook_context.get("modelId", "N/A")
        version_id = webhook_context.get("versionId", "N/A")
        
        # Creiamo un "mini-ctx" per il reporting per non fare confusione
        safe_ctx = type('SafeContext', (), {
            'speckle_server_url': server_url,
            'project_id': project_id,
            'model': type('Model', (), {'id': model_id})(),
            'version_id': version_id
        })()

        with open(html_report_path, "w", encoding='utf-8') as f:
            f.write(create_html_report(all_errors_structured, safe_ctx))
        create_csv_export(all_errors_structured, safe_ctx, csv_export_path)
        
        try:
            ctx.store_result_blobs([html_report_path, csv_export_path])
            print("Report HTML e CSV salvati e allegati con successo.")
        except AttributeError:
            print("ATTENZIONE: La funzione 'store_result_blobs' non è supportata. I report non sono stati allegati.")
        except Exception as e:
            print(f"ERRORE durante il salvataggio dei report: {e}")

        if total_issues > 0:
            # ... (logica di fallimento e notifica come prima)
            ctx.mark_run_failed(f"Validazione fallita con {total_issues} problemi.")
        else:
            # ... (logica di successo come prima)
            ctx.mark_run_success("Validazione completata.")

    except Exception as e:
        # ... (logica di errore critico come prima)

    print("--- GOLDEN MASTER SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
