# main.py
# Script di diagnosi definitiva per ispezionare la struttura dell'oggetto parametro
# 'Sigillatura_Rei_Installation' di una porta.

import inspect
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
OPENING_CATEGORIES = ["Porte", "Finestre"] 
FIRE_SEAL_PARAM = "Sigillatura_Rei_Installation"
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
    Esegue una diagnosi sulla struttura del parametro 'Sigillatura_Rei_Installation'.
    """
    print("--- RUNNING DIAGNOSTIC FOR RULE #3 ---", flush=True)
    
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in OPENING_CATEGORIES):
            print(f"\n-> Found target opening {el.id} (Category: {category})", flush=True)
            
            try:
                properties = getattr(el, 'properties')
                revit_parameters = properties['Parameters']
                instance_params = revit_parameters['Instance Parameters']
                
                param_object = None
                # Iteriamo su tutti i gruppi per trovare il nostro parametro
                for group_name, group_content in instance_params.items():
                    if isinstance(group_content, dict) and FIRE_SEAL_PARAM in group_content:
                        param_object = group_content[FIRE_SEAL_PARAM]
                        print(f"   SUCCESS: Found '{FIRE_SEAL_PARAM}' parameter object in group '{group_name}'.", flush=True)
                        break
                
                if not param_object:
                    raise ValueError(f"'{FIRE_SEAL_PARAM}' not found in any instance parameter group.")

                # --- ISPEZIONE FINALE ---
                print("   --- INSPECTING THE PARAMETER OBJECT ---", flush=True)
                print(f"   Parameter Object Type: {type(param_object)}", flush=True)
                print("   Available attributes and methods:", flush=True)
                
                # Usiamo dir() per ottenere una "radiografia" completa dell'oggetto.
                for attr in dir(param_object):
                    print(f"     - {attr}", flush=True)

                # Proviamo a vedere se ha un attributo 'value' e stampiamolo.
                final_value = getattr(param_object, 'value', "ATTRIBUTE 'value' NOT FOUND")
                print(f"   Attempting to get '.value': {final_value}", flush=True)
                
                # Proviamo anche a leggerlo come un dizionario
                try:
                    dict_value = param_object.get("value")
                    print(f"   Attempting to get .get('value'): {dict_value}", flush=True)
                except Exception:
                    print("   Attempting to get .get('value'): FAILED", flush=True)

                print("   --------------------------------------", flush=True)
                # Usciamo dopo aver ispezionato il primo oggetto.
                return []

            except (AttributeError, KeyError, ValueError) as e:
                print(f"   DIAGNOSTIC FAILED for element {el.id}: {e}", flush=True)
                continue

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

        run_penetration_check_diagnostic(all_elements, ctx)
        
        ctx.mark_run_success("Diagnostic complete. Check logs for details.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- END OF FINAL DIAGNOSTIC SCRIPT ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
