# main.py
# Script di diagnosi definitiva per ispezionare la struttura completa dei parametri di una porta.

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
    Esegue una diagnosi sulla struttura completa dei parametri della prima apertura trovata.
    """
    print("--- RUNNING DIAGNOSTIC FOR RULE #3 ---", flush=True)
    
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in OPENING_CATEGORIES):
            print(f"\n-> Found target opening {el.id} (Category: {category})", flush=True)
            
            try:
                properties = getattr(el, 'properties')
                revit_parameters = properties.get('Parameters', {})
                
                # --- ISPEZIONE FINALE E COMPLETA ---
                print("   --- INSPECTING INSTANCE PARAMETERS ---", flush=True)
                instance_params = revit_parameters.get('Instance Parameters', {})
                if instance_params:
                    for group_name, group_content in instance_params.items():
                        print(f"     - Group: {group_name}", flush=True)
                        if isinstance(group_content, dict):
                            for param_name in group_content.keys():
                                print(f"       - Param: {param_name}", flush=True)
                else:
                    print("     No Instance Parameters found.", flush=True)

                print("\n   --- INSPECTING TYPE PARAMETERS ---", flush=True)
                type_params = revit_parameters.get('Type Parameters', {})
                if type_params:
                    for group_name, group_content in type_params.items():
                        print(f"     - Group: {group_name}", flush=True)
                        if isinstance(group_content, dict):
                            for param_name in group_content.keys():
                                print(f"       - Param: {param_name}", flush=True)
                else:
                    print("     No Type Parameters found.", flush=True)

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
