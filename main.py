# main.py
# Script di diagnosi definitiva per ispezionare la struttura completa e i VALORI dei parametri di TUTTE le porte.

import inspect
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
OPENING_CATEGORIES = ["Porte", "Finestre"] 
FIRE_SEAL_PARAM = "Sigillatura_Rei_Installation"
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


#============== DIAGNOSI PER LA REGOLA #3 ===========================================
def run_penetration_check_diagnostic(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue una diagnosi sulla struttura completa e sui valori dei parametri di TUTTE le aperture trovate.
    """
    print("--- RUNNING DIAGNOSTIC FOR RULE #3 ---", flush=True)
    
    openings_found = 0
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in OPENING_CATEGORIES):
            openings_found += 1
            print(f"\n-> Found target opening #{openings_found}: {el.id} (Category: {category})", flush=True)
            
            try:
                # --- ISPEZIONE FINALE E COMPLETA ---
                properties = getattr(el, 'properties', {})
                revit_parameters = properties.get('Parameters', {})
                instance_params = revit_parameters.get('Instance Parameters', {})
                text_group = instance_params.get(PARAMETER_GROUP, {})
                seal_param_dict = text_group.get(FIRE_SEAL_PARAM)

                if seal_param_dict:
                    # Stampiamo il valore e il suo tipo!
                    value = seal_param_dict.get("value")
                    print(f"   SUCCESS: Found '{FIRE_SEAL_PARAM}'. Value: '{value}' (Type: {type(value)})", flush=True)
                else:
                    print(f"   WARNING: Parameter '{FIRE_SEAL_PARAM}' not found in group '{PARAMETER_GROUP}'.", flush=True)

            except Exception as e:
                print(f"   DIAGNOSTIC FAILED for element {el.id}: {e}", flush=True)
                continue

    if openings_found == 0:
        print("No openings (Doors/Windows) found in the commit.", flush=True)
    
    return []


#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    """
    Funzione principale che orchestra l'esecuzione di tutte le regole di validazione.
    """
    print("--- STARTING FINAL DIAGNOSTIC SCRIPT ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("No Revit elements found in the commit.")
            return

        print(f"Found {len(all_elements)} total elements to analyze.", flush=True)

        # Eseguiamo solo lo script di diagnosi
        run_penetration_check_diagnostic(all_elements, ctx)
        
        ctx.mark_run_success("Diagnostic complete. Check logs for details.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- END OF FINAL DIAGNOSTIC SCRIPT ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
