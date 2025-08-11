# main.py
# VERSIONE 13.6 - AUTODIAGNOSI OGGETTO

import json
import requests
import traceback
import os
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE E CHIAVI SEGRETE ==============================
GEMINI_API_KEY = "AIzaSyC7zV4v755kgFK2tClm1EaDtoQFnAHQjeg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398412307830145165/2QpAJDDmDnVsBezBVUXKbwHubYw60QTNWR-oLyn0N9MR73S0u8LRgAhgwmz9Q907CNCb"

# --- Nomi dei Gruppi Parametri (in Italiano) ---
GRUPPO_TESTO = "Testo"
GRUPPO_DATI_IDENTITA = "Dati identità"

# --- Regole Antincendio ---
FIRE_TARGET_CATEGORIES = ["Muri", "Pavimenti", "Telai Strutturali", "Pilastri", 
                          "Walls", "Floors", "Structural Framing", "Structural Columns"]
FIRE_OPENING_CATEGORIES = ["Porte", "Finestre", "Doors", "Windows"]
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"

# --- Regole Costi ---
COST_DESC_PARAM_NAME = "Descrizione"
COST_UNIT_PARAM_NAME = "Costo_Unitario"
BUDGETS = {"Muri": 120000, "Pavimenti": 50000, "Walls": 120000, "Floors": 50000}
#=====================================================================================

#============== FUNZIONI HELPER ======================================================
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

#============== FUNZIONE DI DIAGNOSI =================================================
def run_diagnostic_check(elements: list):
    """
    Analizza il primo elemento con un costo e stampa la sua struttura dati.
    """
    print("--- RUNNING DIAGNOSTIC MODE ---", flush=True)
    
    element_to_debug = None
    for el in elements:
        # Usiamo il nome del gruppo corretto in italiano
        cost_val = get_instance_parameter_value(el, GRUPPO_TESTO, COST_UNIT_PARAM_NAME)
        if cost_val is not None:
            element_to_debug = el
            break

    if element_to_debug:
        print("\n\n" + "="*30)
        print("--- INIZIO AUTODIAGNOSI OGGETTO ---")
        print(f"Sto analizzando l'elemento con ID: {element_to_debug.id}")
        print(f"Categoria: {getattr(element_to_debug, 'category', 'N/A')}")
        
        # Tentiamo di stampare l'intera struttura 'properties' in modo leggibile
        if hasattr(element_to_debug, 'properties'):
            print("\n--- Contenuto di 'element.properties': ---")
            try:
                # Usiamo json.dumps per una stampa pulita e indentata
                # ensure_ascii=False serve per stampare correttamente caratteri italiani come 'à'
                print(json.dumps(element_to_debug.properties, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"Impossibile stampare 'properties' come JSON: {e}")
                print("--- Contenuto grezzo di 'element.properties': ---")
                try:
                    # dir() elenca tutti gli attributi dell'oggetto
                    print(dir(element_to_debug.properties))
                except Exception as dir_e:
                    print(f"Impossibile ispezionare 'properties' in modo grezzo: {dir_e}")
        else:
            print("\nL'oggetto non ha un attributo 'properties'.")

        print("\n--- FINE AUTODIAGNOSI OGGETTO ---")
        print("="*30 + "\n\n")
    else:
        print("\n--- NESSUN ELEMENTO TROVATO CON IL PARAMETRO 'Costo_Unitario' COMPILATO ---")
        print("Assicurati che almeno un elemento nel commit abbia questo parametro di istanza nel gruppo 'Testo'.")

    return

#============== ORCHESTRATORE PRINCIPALE (DIAGNOSTICO) =======================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING DIAGNOSTIC VALIDATOR (v13.6) ---", flush=True)
    try:
        all_elements = find_all_elements(ctx.receive_version())
        if not all_elements:
            ctx.mark_run_success("Nessun elemento processabile.")
            return

        print(f"Trovati {len(all_elements)} elementi da analizzare.", flush=True)
        
        # Eseguiamo solo la funzione di diagnosi
        run_diagnostic_check(all_elements)
        
        ctx.mark_run_success("Diagnosi completata. Controllare il log per i dettagli della struttura dati.")

    except Exception as e:
        error_message = f"Errore critico: {e}"
        traceback.print_exc()
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- DIAGNOSTIC SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
