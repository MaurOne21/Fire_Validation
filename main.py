# main.py
# VERSIONE 19.1 - AI REALE (SINTASSI CORRETTA)

import json
import requests
import traceback
import os
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ==============================
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

# --- Nomi dei Gruppi Parametri (in Italiano) ---
GRUPPO_TESTO = "Testo"
GRUPPO_DATI_IDENTITA = "Dati identità"

# --- Regole Antincendio ---
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Telai Strutturali", "Pilastri", "Walls", "Floors", "Structural Framing", "Structural Columns"]
FIRE_RATING_PARAM = "Fire_Rating"

# --- Regole Costi ---
COST_DESC_PARAM_NAME = "Descrizione"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
#=====================================================================================


#============== FUNZIONI HELPER ======================================================
def find_all_elements(base_object) -> list:
    elements = []
    element_container = getattr(base_object, '@elements', None) or getattr(base_object, 'elements', None)
    if element_container and isinstance(element_container, list):
        for element in element_container: elements.extend(find_all_elements(element))
    elif isinstance(base_object, list):
        for item in base_object: elements.extend(find_all_elements(item))
    
    # ⬇️⬇️⬇️ ECCO LA CORREZIONE ⬇️⬇️⬇️
    element_id = getattr(base_object, 'id', None)
    if element_id not in (None, "") and "Objects.Organization.Model" not in getattr(base_object, 'speckle_type', ''):
        elements.append(base_object)
    return elements

def get_ai_suggestion(prompt: str, is_json_response: bool = True) -> str:
    if not GEMINI_API_KEY or "INCOLLA_QUI" in GEMINI_API_KEY:
        print("ATTENZIONE: Chiave API di Gemini non configurata.")
        if is_json_response: return '{"justification": "AI non configurata."}'
        return "AI non configurata."

    print(f"Chiamando l'API di Gemini con prompt: {prompt[:80]}...")
    
    headers = {"Content-Type": "application/json"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
    final_prompt = prompt
    if is_json_response:
        final_prompt += "\nRispondi SOLO con un oggetto JSON valido, senza ```json o altre formattazioni."

    payload = {"contents": [{"parts": [{"text": final_prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        
        json_response = response.json()
        
        # Percorso robusto per estrarre il testo
        candidates = json_response.get("candidates", [])
        if not candidates:
            raise KeyError("Nessun 'candidates' nella risposta.")
        
        content = candidates.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise KeyError("Nessuna 'parts' nel contenuto.")
            
        text_response = parts.get("text", "").strip()
        print(f"Risposta ricevuta da Gemini: {text_response}")
        return text_response

    except requests.exceptions.RequestException as e:
        print(f"ERRORE: La chiamata all'API di Gemini è fallita: {e}")
        if is_json_response: return '{"justification": "Chiamata API fallita."}'
        return "Errore nella chiamata API."
    except (KeyError, IndexError) as e:
        print(f"ERRORE: La risposta di Gemini non ha il formato atteso: {e}. Risposta completa: {json_response}")
        if is_json_response: return '{"justification": "Risposta AI non valida."}'
        return "Formato risposta AI non valido."

def send_webhook_notification(title: str, description: str, color: int, fields: list):
    if not WEBHOOK_URL or "INCOLLA_QUI" in WEBHOOK_URL: return
    embed = {"title": title, "description": description, "color": color, "fields": fields}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except Exception as e: print(f"Errore invio notifica: {e}")

#============== FUNZIONI DELLE REGOLE ================================================
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

def run_ai_cost_check(elements: list, price_list: list) -> list:
    print("--- RUNNING RULE #5: AI COST CHECK (REAL AI) ---", flush=True)
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
        
        ai_prompt = (
            f"Agisci come un esperto computista. Valuta questo costo unitario:\n"
            f"- Descrizione: '{search_description}'\n"
            f"- Costo nel Modello: €{model_cost:.2f}\n"
            f"- Costo di Riferimento da Prezzario: €{ref_cost:.2f}\n"
            f"Il costo nel modello è palesemente irragionevole (es. zero, troppo basso o troppo alto)? "
            f"Giustifica la tua risposta. Fornisci anche un costo suggerito se lo ritieni errato.\n"
            f"La tua risposta DEVE essere un oggetto JSON con tre chiavi: 'is_consistent' (boolean), "
            f"'justification' (stringa concisa), e 'suggested_cost' (numero o null)."
        )
        
        ai_response_str = get_ai_suggestion(ai_prompt, is_json_response=True)
        
        try:
            ai_response = json.loads(ai_response_str)
            if not ai_response.get("is_consistent"):
                justification = ai_response.get('justification', 'N/A')
                suggestion = ai_response.get('suggested_cost')
                warning_message = f"AI: {justification}"
                if suggestion:
                    warning_message += f" (Suggerito: ~€{suggestion:.2f})"
                cost_warnings.append((el, warning_message))
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"ERRORE nell'interpretare la risposta JSON dell'AI: {e} -> Risposta ricevuta: {ai_response_str}")
            
    print(f"Rule #5 Finished. {len(cost_warnings)} cost issues found.", flush=True)
    return cost_warnings

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING REAL-AI VALIDATOR (v19.1) ---", flush=True)
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
        cost_warnings = run_ai_cost_check(all_elements, price_list)
        
        total_issues = len(fire_rating_errors) + len(cost_warnings)

        if total_issues > 0:
            if fire_rating_errors:
                ctx.attach_error_to_objects(category="Dato Mancante: Fire_Rating", affected_objects=fire_rating_errors, message="Manca il parametro 'Fire_Rating'.")
            if cost_warnings:
                ctx.attach_warning_to_objects(
                    category="Costo Non Congruo (AI)",
                    affected_objects=[item for item in cost_warnings],
                    message="Il costo unitario non è congruo secondo l'analisi AI."
                )

            summary_desc = "Validazione completata."
            fields, error_counts = [], {}
            if fire_rating_errors: error_counts["Dato Antincendio Mancante"] = len(fire_rating_errors)
            if cost_warnings: error_counts["Costo Non Congruo (AI)"] = len(cost_warnings)
            for rule_desc, count in error_counts.items():
                 fields.append({"name": f"⚠️ {rule_desc}", "value": f"**{count}** problemi", "inline": True})
            
            ai_summary_prompt = f"Agisci come un Project Manager. Un controllo automatico ha trovato questi problemi: {', '.join(error_counts.keys())}. Riassumi le priorità strategiche in una frase concisa."
            ai_suggestion = get_ai_suggestion(ai_summary_prompt, is_json_response=False)
            fields.append({"name": "🤖 Analisi Strategica (AI)", "value": ai_suggestion, "inline": False})
            
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

    print("--- REAL-AI SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
