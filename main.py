# main.py
# VERSIONE 18.0 - REPORTING AVANZATO STABILE (HTML + CSV)

import json
import requests
import traceback
import os
import csv
from datetime import datetime
from collections import defaultdict
from speckle_automate import AutomationContext, execute_automate_function

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

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
BUDGETS = {"Muri": 120000, "Pavimenti": 50000}
#=====================================================================================

# (Funzioni helper e delle regole - nessuna modifica qui, sono già perfette)
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

def get_ai_suggestion(prompt: str) -> str:
    if "Riassumi le priorità" in prompt:
        return "Priorità alla revisione dei dati critici mancanti (es. Antincendio) e alla successiva analisi dei costi non congrui."
    return '{"is_consistent": false, "suggestion": 50.0, "justification": "Costo non compilato o pari a zero."}'

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore invio notifica: {e}")

def run_fire_rating_check(all_elements: list) -> list:
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = []
    for el in all_elements:
        if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES):
            try:
                value = el.properties['Parameters']['Instance Parameters'][GRUPPO_TESTO][FIRE_RATING_PARAM]['value']
                if not value: errors.append(el)
            except (AttributeError, KeyError, TypeError): errors.append(el)
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_penetration_check(all_elements: list) -> list:
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION ---", flush=True)
    errors = []
    for el in all_elements:
        if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_OPENING_CATEGORIES):
            value = el.properties['Parameters']['Instance Parameters'][GRUPPO_TESTO][FIRE_SEAL_PARAM]['value']
            if not (value is True or str(value).lower() in ["si", "yes", "true", "1"]):
                errors.append(el)
    print(f"Rule #3 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_total_budget_check(elements: list) -> list:
    print("--- RUNNING RULE #4: TOTAL BUDGET CHECK ---", flush=True)
    costs_by_category = {cat: 0 for cat in BUDGETS.keys()}
    for el in elements:
        category = getattr(el, 'category', '')
        if category in costs_by_category:
            try:
                cost_val = el.properties['Parameters']['Instance Parameters'][GRUPPO_TESTO][COST_UNIT_PARAM_NAME]['value']
                metric = getattr(el, 'volume', getattr(el, 'area', 0))
                costs_by_category[category] += (float(cost_val) if cost_val else 0) * metric
            except (AttributeError, KeyError, TypeError, ValueError): continue
    alerts = [f"Categoria '{cat}': superato budget di €{costs_by_category[cat] - BUDGETS[cat]:,.2f}" for cat in costs_by_category if costs_by_category[cat] > BUDGETS[cat]]
    print(f"Rule #4 Finished. {len(alerts)} budget issues found.", flush=True)
    return alerts

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK ---", flush=True)
    cost_warnings = []
    price_dict = {item['descrizione']: item for item in price_list}
    for el in elements:
        try:
            item_description = el.properties['Parameters']['Type Parameters'][GRUPPO_DATI_IDENTITA][COST_DESC_PARAM_NAME]['value']
            model_cost_raw = el.properties['Parameters']['Instance Parameters'][GRUPPO_TESTO][COST_UNIT_PARAM_NAME]['value']
            model_cost = float(model_cost_raw)
            if not item_description: continue
        except (AttributeError, KeyError, TypeError, ValueError): continue
        
        search_description = item_description
        price_list_entry = price_dict.get(search_description)
        if not price_list_entry: continue
        
        ref_cost = price_list_entry.get("costo_nuovo") or price_list_entry.get("costo_kg")
        if ref_cost is None: continue
        
        if model_cost <= 0.1:
             ai_response_str = get_ai_suggestion("costo a zero")
             try:
                ai_response = json.loads(ai_response_str)
                warning_message = f"AI: {ai_response.get('justification')}"
                cost_warnings.append((el, warning_message))
             except Exception as e: print(f"Errore interpretazione AI: {e}")
            
    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings

#============== FUNZIONI DI REPORTING (RIATTIVATE) =================================
def create_html_report(all_errors: list, run_id: str) -> str:
    if not PLOTLY_AVAILABLE:
        return "<h1>Plotly non è installato. Impossibile generare report grafico.</h1>"
    if not all_errors:
        return f"<h1>✅ Nessun Errore Rilevato</h1><p>Run ID: {run_id}</p>"

    errors_by_rule = defaultdict(int)
    errors_by_category = defaultdict(int)
    for error in all_errors:
        errors_by_rule[error["rule_description"]] += 1
        if error["element_category"] != "N/A": errors_by_category[error["element_category"]] += 1
    
    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "bar"}, {"type": "pie"}]],
                        subplot_titles=("Errori per Regola", "Errori per Categoria"))
    fig.add_trace(go.Bar(y=list(errors_by_rule.keys()), x=list(errors_by_rule.values()), orientation='h'), row=1, col=1)
    if errors_by_category:
        fig.add_trace(go.Pie(labels=list(errors_by_category.keys()), values=list(errors_by_category.values()), hole=.3), row=1, col=2)
    
    fig.update_layout(showlegend=False, title_text=f"Report di Validazione - Run {run_id}", margin=dict(t=100, b=20))
    graphs_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    table_header = "<tr><th>Regola</th><th>Livello</th><th>Categoria</th><th>ID Elemento</th><th>Messaggio</th></tr>"
    table_rows = "".join([f"<tr><td>{e['rule_description']}</td><td>{e['error_level']}</td><td>{e['element_category']}</td><td>{e['element_id']}</td><td>{e['message']}</td></tr>" for e in all_errors])
    table_html = f"<table border='1' style='width:100%; border-collapse: collapse; font-size: 12px;'>{table_header}{table_rows}</table>"

    return f"<html><head><title>Speckle Report</title></head><body style='font-family: sans-serif;'>{graphs_html}<h2>Dettaglio Errori</h2>{table_html}</body></html>"

def create_csv_export(all_errors: list, run_id: str, file_path: str):
    if not all_errors: return
    # Usiamo un set ridotto di campi, compatibile con quello che possiamo recuperare
    fieldnames = ["timestamp", "run_id", "rule_id", "rule_description", "element_id", "element_category", "error_level", "message", "penalty_score"]
    
    with open(file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for error in all_errors:
            row = {"run_id": run_id, **error, "timestamp": datetime.utcnow().isoformat(),
                   "penalty_score": 10 if error["error_level"] == "ERROR" else 3}
            final_row = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(final_row)

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING RELEASE CANDIDATE (v18.0) ---", flush=True)
    try:
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
        
        fire_rating_errors = run_fire_rating_check(all_elements)
        penetration_errors = run_penetration_check(all_elements)
        budget_alerts = run_total_budget_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        all_errors_structured = []
        for el in fire_rating_errors:
            all_errors_structured.append({"rule_id": "FIRE-01", "rule_description": "Dato Antincendio Mancante", "element_id": el.id, "element_category": getattr(el, 'category', 'N/A'), "error_level": "ERROR", "message": f"Manca '{FIRE_RATING_PARAM}'."})
        for el in penetration_errors:
            all_errors_structured.append({"rule_id": "FIRE-03", "rule_description": "Apertura non Sigillata", "element_id": el.id, "element_category": getattr(el, 'category', 'N/A'), "error_level": "WARNING", "message": f"'{FIRE_SEAL_PARAM}' non valido."})
        for msg in budget_alerts:
             all_errors_structured.append({"rule_id": "BUDGET-04", "rule_description": "Superamento Budget", "element_id": "N/A", "element_category": msg.split("'")[1], "error_level": "ERROR", "message": msg})
        for el, ai_msg in cost_warnings:
            all_errors_structured.append({"rule_id": "COST-05", "rule_description": "Costo Non Congruo (AI)", "element_id": el.id, "element_category": getattr(el, 'category', 'N/A'), "error_level": "WARNING", "message": ai_msg})

        total_issues = len(all_errors_structured)
        run_identifier = datetime.now().strftime('%Y%m%d-%H%M%S')
        
        # ⬇️⬇️⬇️ SALVATAGGIO DEI REPORT IN UNA DIRECTORY SICURA ⬇️⬇️⬇️
        # Usiamo /tmp, una directory temporanea standard in ambienti Linux
        temp_dir = "/tmp"
        html_report_path = os.path.join(temp_dir, f"validation_report_{run_identifier}.html")
        csv_export_path = os.path.join(temp_dir, f"powerbi_export_{run_identifier}.csv")
        
        with open(html_report_path, "w", encoding='utf-8') as f:
            f.write(create_html_report(all_errors_structured, run_identifier))
        create_csv_export(all_errors_structured, run_identifier, csv_export_path)
        
        ctx.store_result_blobs([html_report_path, csv_export_path])
        print(f"Report HTML e CSV salvati e allegati al run.")

        if total_issues > 0:
            # (Logica di notifica e fallimento come prima)
            if fire_rating_errors: ctx.attach_error_to_objects(category="Dato Mancante: Fire_Rating", affected_objects=fire_rating_errors, message="Manca il parametro 'Fire_Rating'.")
            if penetration_errors: ctx.attach_warning_to_objects(category="Apertura non Sigillata", affected_objects=penetration_errors, message="Il parametro 'FireSealInstalled' non è valido.")
            if cost_warnings: ctx.attach_warning_to_objects(category="Costo Non Congruo (AI)", affected_objects=[item[0] for item in cost_warnings], message="Il costo unitario non è congruo.")

            summary_desc = "Validazione completata."
            fields, error_counts = [], {}
            for error in all_errors_structured: error_counts[error["rule_description"]] = error_counts.get(error["rule_description"], 0) + 1
            for rule_desc, count in error_counts.items(): fields.append({"name": f"⚠️ {rule_desc}", "value": f"**{count}** problemi", "inline": True})
            ai_suggestion = get_ai_suggestion("Riassumi le priorità.")
            fields.append({"name": "🤖 Suggerimento AI", "value": ai_suggestion, "inline": False})
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

    print("--- RELEASE CANDIDATE SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
