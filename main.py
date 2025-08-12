# main.py
# VERSIONE 19.6 - DIAGNOSI RISPOSTA AI

import json
import requests
import traceback
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ==============================
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"

#============== FUNZIONE DI DIAGNOSI ==================================
def diagnose_ai_response():
    print("--- ESEGUO DIAGNOSI RISPOSTA AI ---")
    if not GEMINI_API_KEY or "INCOLLA_QUI" in GEMINI_API_KEY:
        print("Chiave API non configurata.")
        return

    headers = {"Content-Type": "application/json"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = "Ciao, rispondi solo 'OK'."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        json_response = response.json()
        
        print("\n\n" + "="*30)
        print("--- RISPOSTA GREZZA DALL'API DI GEMINI ---")
        print(json.dumps(json_response, indent=2))
        print("="*30 + "\n\n")

    except Exception as e:
        print(f"ERRORE DURANTE LA CHIAMATA API: {e}")

#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING AI RESPONSE DIAGNOSTIC (v19.6) ---", flush=True)
    try:
        diagnose_ai_response()
        ctx.mark_run_success("Diagnosi completata. Controllare il log per la risposta grezza dell'API.")

    except Exception as e:
        error_message = f"Errore critico: {e}"
        traceback.print_exc()
        ctx.mark_run_failed(error_message)

    print("--- AI DIAGNOSTIC SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
