# main.py
# Script di diagnosi definitiva per ispezionare i VALORI dei parametri nelle Regole #1 e #3.

import json
import requests
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
# --- Regole ---
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti"]
OPENING_CATEGORIES = ["Porte", "Finestre"] 
FIRE_RATING_PARAM = "Fire_Rating"
FIRE_SEAL_PARAM = "FireSealInstalled"
PARAMETER_GROUP = "Testo"
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


#============== DIAGNOSI PER LE REGOLE #1 E #3 ========================================
def run_fire_rating_diagnostic(all_elements: list, ctx: AutomationContext):
    """
    Esegue una diagnosi sulla Regola #1, stampando i valori trovati.
    """
    print("--- RUNNING DIAGNOSTIC FOR RULE #1 ---", flush=True)
    
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in TARGET_CATEGORIES_RULE_1):
            print(f"-> Found target element {el.id} (Category: {category})", flush=True)
            try:
                properties = getattr(el, 'properties')
                revit_parameters = properties['Parameters']
                instance_params = revit_parameters['Instance Parameters']
                text_group = instance_params[PARAMETER_GROUP]
                fire_rating_param_dict = text_group[FIRE_RATING_PARAM]
                value = fire_rating_param_dict.get("value")
                print(f"   SUCCESS: Found '{FIRE_RATING_PARAM}'. Value: '{value}' (Type: {type(value)})", flush=True)
            except (AttributeError, KeyError) as e:
                print(f"   DIAGNOSTIC FAILED for element {el.id}: Could not find the parameter. Reason: {e}", flush=True)

def run_penetration_check_diagnostic(all_elements: list, ctx: AutomationContext):
    """
    Esegue una diagnosi sulla Regola #3, stampando i valori trovati.
    """
    print("--- RUNNING DIAGNOSTIC FOR RULE #3 ---", flush=True)
    
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in OPENING_CATEGORIES):
            print(f"-> Found target opening {el.id} (Category: {category})", flush=True)
            try:
                properties = getattr(el, 'properties', {})
                revit_parameters = properties.get('Parameters', {})
                instance_params = revit_parameters.get('Instance Parameters', {})
                text_group = instance_params.get(PARAMETER_GROUP, {})
                seal_param_dict = text_group.get(FIRE_SEAL_PARAM)
                if seal_param_dict:
                    value = seal_param_dict.get("value")
                    print(f"   SUCCESS: Found '{FIRE_SEAL_PARAM}'. Value: '{value}' (Type: {type(value)})", flush=True)
                else:
                    print(f"   WARNING: Parameter '{FIRE_SEAL_PARAM}' not found in group '{PARAMETER_GROUP}'.", flush=True)
            except Exception as e:
                print(f"   DIAGNOSTIC FAILED for element {el.id}: {e}", flush=True)


#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    """
    Funzione principale che esegue gli script di diagnosi.
    """
    print("--- STARTING FINAL DIAGNOSTIC SCRIPT ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("No Revit elements found in the commit.")
            return

        print(f"Found {len(all_elements)} total elements to analyze.", flush=True)

        # Eseguiamo solo gli script di diagnosi
        run_fire_rating_diagnostic(all_elements, ctx)
        run_penetration_check_diagnostic(all_elements, ctx)
        
        ctx.mark_run_success("Diagnostic complete. Check logs for details.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- VALIDATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
