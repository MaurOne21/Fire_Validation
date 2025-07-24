# main.py
# Script di diagnosi per la Regola #2. Ispeziona la funzione 'ctx.get_model'
# per scoprire i suoi argomenti corretti.

import inspect
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti"]
FIRE_RATING_PARAM = "Fire_Rating"
PARAMETER_GROUP = "Testo"
STRUCTURAL_STREAM_ID = "d48a1d3b3c" 
#=====================================================================================


def find_all_elements(base_object) -> list:
    """
    Cerca ricorsivamente in un oggetto Speckle tutti gli elementi.
    """
    all_elements = []
    elements_property = getattr(base_object, 'elements', None)
    if not elements_property:
        elements_property = getattr(base_object, '@elements', None)

    if elements_property and isinstance(elements_property, list):
        for element in elements_property:
            all_elements.extend(find_all_elements(element))
    elif "Collection" not in getattr(base_object, "speckle_type", ""):
        all_elements.append(base_object)
    return all_elements


#============== LOGICA DELLA REGOLA #1 (FUNZIONANTE) =================================
def run_fire_rating_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #1: Verifica che tutti i muri e solai abbiano
    il parametro 'Fire_Rating' compilato.
    """
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    validation_errors = []
    # ... (la logica della Regola #1 rimane qui, ma per il test possiamo saltarla)
    print(f"Rule #1 Finished. Skipping logic for this test.", flush=True)
    return validation_errors


#============== DIAGNOSI PER LA REGOLA #2 ===========================================
def run_demolition_check_diagnostic(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue una diagnosi sulla funzione 'ctx.get_model'.
    """
    print("--- RUNNING DIAGNOSTIC FOR RULE #2 ---", flush=True)
    
    try:
        print("\n--- Analisi della funzione 'ctx.get_model' ---", flush=True)
        
        # Usiamo il modulo 'inspect' per ottenere la firma della funzione
        signature = inspect.signature(ctx.get_model)
        parameters = signature.parameters
        
        print("Parametri richiesti dalla funzione 'get_model':", flush=True)
        
        param_names = list(parameters.keys())
        for name in param_names:
            print(f"  - {name}", flush=True)
            
        print("\n--- Diagnosi completata ---", flush=True)

    except Exception as e:
        print(f"DIAGNOSTIC FAILED: {e}", flush=True)

    return []


#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    """
    Funzione principale che orchestra l'esecuzione di tutte le regole di validazione.
    """
    print("--- STARTING VALIDATION SCRIPT ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("No Revit elements found in the commit.")
            return

        print(f"Found {len(all_elements)} total elements to analyze.", flush=True)

        all_errors = []
        all_errors.extend(run_fire_rating_check(all_elements, ctx))
        # Eseguiamo la nostra funzione di diagnosi invece della regola vera e propria
        all_errors.extend(run_demolition_check_diagnostic(all_elements, ctx))
        
        if all_errors:
            ctx.mark_run_failed(f"Validation failed with a total of {len(all_errors)} errors.")
        else:
            ctx.mark_run_success("Validation passed: All rules were successful.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- VALIDATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
