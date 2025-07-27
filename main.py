# main.py
# VERSIONE 11.0 - SPECKLECON EDITION (HYBRID REPORTING: HTML + POWER BI EXPORT)

import json
import requests
import traceback
import os
import csv
from datetime import datetime
from speckle_automate import AutomationContext, execute_automate_function

# Tentativo di importare Plotly per i grafici
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

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
BUDGETS = {"Muri": 120000, "Pavimenti": 50000, "Walls": 120000, "Floors": 50000}
#=====================================================================================

# (Tutte le funzioni helper e le funzioni delle regole sono definite qui)
def find_all_elements(base_object) -> list:
    # ... (codice identico a prima)
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
    # ... (codice identico alla v8.4)
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
    # ... (codice identico a prima)
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    print(f"Invio notifica webhook a Discord: {title}")
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)
    except Exception as e: print(f"Errore durante l'invio della notifica a Discord: {e}")

def run_fire_rating_check(all_elements: list) -> list:
    # ... (codice identico a prima)
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    errors = [el for el in all_elements if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_TARGET_CATEGORIES) and not get_instance_parameter_value(el, COST_PARAM_GROUP, FIRE_RATING_PARAM)]
    print(f"Rule #1 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_penetration_check(all_elements: list) -> list:
    # ... (codice identico a prima)
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION (BOOLEAN CHECK) ---", flush=True)
    errors = []
    for el in all_elements:
        if any(target.lower() in getattr(el, 'category', '').lower() for target in FIRE_OPENING_CATEGORIES):
            value = get_instance_parameter_value(el, COST_PARAM_GROUP, FIRE_SEAL_PARAM)
            is_sealed = value is True or str(value).lower() in ["si", "yes", "true", "1"]
            if not is_sealed:
                errors.append(el)
    print(f"Rule #3 Finished. {len(errors)} errors found.", flush=True)
    return errors

def run_total_budget_check(elements: list) -> list:
    # ... (codice identico a prima)
    print("--- RUNNING RULE #4: TOTAL BUDGET CHECK ---", flush=True)
    costs_by_category = {cat: 0 for cat in BUDGETS.keys()}
    for el in elements:
        category = getattr(el, 'category', '')
        if category in costs_by_category:
            cost_val = get_instance_parameter_value(el, COST_PARAM_GROUP, COST_UNIT_PARAM_NAME)
            metric = getattr(el, 'volume', getattr(el, 'area', 0))
            costs_by_category[category] += (float(cost_val) if cost_val else 0) * metric
    alerts = [f"Categoria '{cat}': superato budget di €{costs_by_category[cat] - BUDGETS[cat]:,.2f}" for cat in costs_by_category if costs_by_category[cat] > BUDGETS[cat]]
    for alert in alerts: print(f"BUDGET ALERT: {alert}", flush=True)
    print(f"Rule #4 Finished. {len(alerts)} budget issues found.", flush=True)
    return alerts


def run_ai_cost_check(elements: list, price_list: list) -> list:
    # ... (codice identico a prima)
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


#============== FUNZIONI DI REPORTING ================================================

def create_html_report(all_errors: list, run_context: dict) -> str:
    if not PLOTLY_AVAILABLE:
        return "<h1>Plotly non disponibile. Impossibile generare report grafico.</h1>"
    if not all_errors:
        return f"<h1>✅ Nessun Errore Rilevato</h1><p>Commit: {run_context['commit_id']}</p>"

    errors_by_rule = {}
    errors_by_category = {}
    for error in all_errors:
        rule, category = error["rule_description"], error["element_category"]
        errors_by_rule[rule] = errors_by_rule.get(rule, 0) + 1
        if category != "N/A": errors_by_category[category] = errors_by_category.get(category, 0) + 1

    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "bar"}, {"type": "pie"}]],
                        subplot_titles=("Errori per Regola", "Errori per Categoria"))
    fig.add_trace(go.Bar(y=list(errors_by_rule.keys()), x=list(errors_by_rule.values()), orientation='h'), row=1, col=1)
    if errors_by_category:
        fig.add_trace(go.Pie(labels=list(errors_by_category.keys()), values=list(errors_by_category.values()), hole=.3), row=1, col=2)
    
    fig.update_layout(showlegend=False, title_text=f"Report di Validazione - Commit {run_context['commit_id']}", margin=dict(t=100, b=20))
    graphs_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    table_header = "<tr><th>Regola</th><th>Livello</th><th>Categoria</th><th>ID Elemento</th><th>Messaggio</th></tr>"
    table_rows = "".join([f"<tr><td>{e['rule_description']}</td><td>{e['error_level']}</td><td>{e['element_category']}</td><td>{e['element_id']}</td><td>{e['message']}</td></tr>" for e in all_errors])
    table_html = f"<table border='1' style='width:100%; border-collapse: collapse;'>{table_header}{table_rows}</table>"

    return f"<html><head><title>Speckle Report</title></head><body style='font-family: sans-serif;'>{graphs_html}<h2>Dettaglio Errori</h2>{table_html}</body></html>"

def create_csv_export(all_errors: list, run_context: dict, file_path: str):
    if not all_errors: return
    fieldnames = ["timestamp", "run_id", "project_id", "model_id", "commit_id", "author_name", "rule_id",
                  "rule_description", "element_id", "element_category", "error_level", "message", "penalty_score"]
    
    with open(file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for error in all_errors:
            row = {**run_context, **error, "timestamp": datetime.utcnow().isoformat(),
                   "penalty_score": 10 if error["error_level"] == "ERROR" else 3}
            # Rimuove le chiavi extra e si assicura che tutte le colonne siano presenti
            final_row = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(final_row)

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING MASTER VALIDATION SCRIPT (WITH HYBRID REPORTING) ---", flush=True)
    try:
        price_list = []
        prezzario_path = os.path.join(os.path.dirname(__file__), 'prezzario.json')
        try:
            with open(prezzario_path, 'r', encoding='utf-8') as f: price_list = json.load(f)
            print("Prezzario 'prezzario.json' caricato.")
        except Exception as e: print(f"ATTENZIONE: 'prezzario.json' non trovato: {e}")

        commit = ctx.get_commit_data()
        run_context = {
            "run_id": ctx.automation_run_id, "project_id": ctx.project_id, "model_id": ctx.model.id,
            "commit_id": ctx.version_id, "author_name": commit.authorName
        }

        all_elements = find_all_elements(ctx.receive_version())
        if not all_elements:
            ctx.mark_run_success("Nessun elemento processabile.")
            return

        print(f"Trovati {len(all_elements)} elementi da analizzare.", flush=True)
        
        fire_rating_errors = run_fire_rating_check(all_elements)
        penetration_errors = run_penetration_check(all_elements)
        budget_alerts = run_total_budget_check(all_elements)
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        all_errors_structured = []
        for el in fire_rating_errors:
            all_errors_structured.append({"rule_id": "FIRE-01", "rule_description": "Dato Antincendio Mancante", "element_id": el.id, "element_category": getattr(el, 'category', 'N/A'), "error_level": "ERROR", "message": f"Manca il parametro '{FIRE_RATING_PARAM}'."})
        for el in penetration_errors:
            all_errors_structured.append({"rule_id": "FIRE-03", "rule_description": "Apertura non Sigillata", "element_id": el.id, "element_category": getattr(el, 'category', 'N/A'), "error_level": "WARNING", "message": f"Il parametro '{FIRE_SEAL_PARAM}' non è valido."})
        for msg in budget_alerts:
             all_errors_structured.append({"rule_id": "BUDGET-04", "rule_description": "Superamento Budget", "element_id": "N/A", "element_category": msg.split("'")[1], "error_level": "ERROR", "message": msg})
        for el, ai_msg in cost_warnings:
            all_errors_structured.append({"rule_id": "COST-05", "rule_description": "Costo Non Congruo (AI)", "element_id": el.id, "element_category": getattr(el, 'category', 'N/A'), "error_level": "WARNING", "message": ai_msg})

        total_issues = len(all_errors_structured)
        temp_path = os.path.dirname(ctx.speckle_token_path)
        html_report_path = os.path.join(temp_path, "validation_report.html")
        with open(html_report_path, "w", encoding='utf-8') as f: f.write(create_html_report(all_errors_structured, run_context))
        csv_export_path = os.path.join(temp_path, "powerbi_export.csv")
        create_csv_export(all_errors_structured, run_context, csv_export_path)
        ctx.store_result_blobs([html_report_path, csv_export_path])

        if total_issues > 0:
            summary_desc, fields, error_summary_for_ai = "Report di Validazione Automatica del Modello:", [], []
            # ... (logica di costruzione notifica come prima)
            ctx.mark_run_failed(f"Validazione fallita con {total_issues} problemi totali.")
        else:
            success_message = "✅ Validazione completata con successo."
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
