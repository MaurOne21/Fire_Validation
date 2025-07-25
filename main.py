# main.py
# Versione di diagnosi per la Regola #3. Ispeziona la struttura dei parametri della prima apertura trovata.

from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
# --- Regola #1 ---
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti"]
FIRE_RATING_PARAM = "Fire_Rating"
PARAMETER_GROUP_RULE_1 = "Testo"

# --- Regola #3 ---
# Usiamo il nome della categoria in italiano che abbiamo scoperto: "Porte"
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


#============== LOGICA DELLA REGOLA #1 (FUNZIONANTE) =================================
def run_fire_rating_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #1: Verifica che tutti i muri e solai abbiano
    il parametro 'Fire_Rating' compilato.
    """
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    
    validation_errors = []
    # La logica è funzionante, la saltiamo per velocizzare il test di diagnosi.
    print(f"Rule #1 Finished. Skipping logic for this test.", flush=True)
    return validation_errors


#============== DIAGNOSI PER LA REGOLA #3 ===========================================
def run_penetration_check_diagnostic(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue una diagnosi sulla struttura dei parametri della prima apertura trovata.
    """
    print("--- RUNNING DIAGNOSTIC FOR RULE #3 ---", flush=True)
    
    # Cerchiamo la prima porta o finestra in tutto il commit.
    for el in all_elements:
        category = getattr(el, 'category', '')
        
        if any(target.lower() in category.lower() for target in OPENING_CATEGORIES):
            
            print(f"\n--- INSPECTING FIRST OPENING FOUND ---", flush=True)
            print(f"Opening ID: {getattr(el, 'id', 'N/A')}", flush=True)
            print(f"Opening Category: {category}", flush=True)
            
            try:
                properties = getattr(el, 'properties')
                revit_parameters = properties['Parameters']
                instance_params = revit_parameters['Instance Parameters']
                
                print("   --- Inspecting 'Instance Parameters' groups and params ---", flush=True)
                for group_name, group_content in instance_params.items():
                    print(f"     - Group: {group_name}", flush=True)
                    if isinstance(group_content, dict):
                        for param_name in group_content.keys():
                            print(f"       - Param: {param_name}", flush=True)
                    else:
                         # Se non è un gruppo, potrebbe essere direttamente un parametro
                         print(f"       - Param (no group): {group_name}", flush=True)


            except (KeyError, AttributeError) as e:
                print(f"     Could not fully inspect the parameter tree. Reason: {e}", flush=True)

            print("   ----------------------------------", flush=True)
            # Usciamo dopo aver ispezionato la prima apertura.
            return []

    print("No openings (Doors/Windows) found in the commit.", flush=True)
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
        all_errors.extend(run_penetration_check_diagnostic(all_elements, ctx))
        
        ctx.mark_run_success("Diagnostic complete. Check logs for details.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- VALIDATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
