# main.py
# Versione di diagnosi per la Regola #3. Ispeziona la struttura dei parametri delle aperture.

from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
# --- Regola #1 ---
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti"]
FIRE_RATING_PARAM = "Fire_Rating"
PARAMETER_GROUP = "Testo"

# --- Regola #3 ---
TARGET_CATEGORIES_RULE_3 = ["Muri"]
OPENING_TYPES = ["Opening", "Door", "Window"] # Tipi di oggetti che rappresentano fori
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
    Esegue una diagnosi sulla struttura dei parametri delle aperture (porte/finestre).
    """
    print("--- RUNNING DIAGNOSTIC FOR RULE #3 ---", flush=True)
    
    fire_rated_walls = []
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in TARGET_CATEGORIES_RULE_3):
            try:
                properties = getattr(el, 'properties')
                revit_parameters = properties['Parameters']
                instance_params = revit_parameters['Instance Parameters']
                text_group = instance_params[PARAMETER_GROUP]
                fire_rating_param_dict = text_group[FIRE_RATING_PARAM]
                value = fire_rating_param_dict.get("value")
                if value and "REI" in str(value):
                    fire_rated_walls.append(el)
            except (AttributeError, KeyError):
                continue
    
    print(f"Found {len(fire_rated_walls)} fire-rated walls.", flush=True)

    for wall in fire_rated_walls:
        openings = getattr(wall, 'elements', [])
        if not openings:
            openings = getattr(wall, '@elements', [])

        if openings:
            # Ispezioniamo solo la prima apertura che troviamo per mantenere i log puliti.
            first_opening = openings[0]
            print(f"\n--- INSPECTING FIRST OPENING IN WALL {wall.id} ---", flush=True)
            print(f"Opening ID: {getattr(first_opening, 'id', 'N/A')}", flush=True)
            print(f"Opening Speckle Type: {getattr(first_opening, 'speckle_type', 'N/A')}", flush=True)
            
            properties = getattr(first_opening, 'properties', None)
            if not properties:
                print("   ERROR: This opening does not have a 'properties' object.", flush=True)
                continue

            print("   --- Contents of 'properties' ---", flush=True)
            if isinstance(properties, dict):
                for key in properties.keys():
                    print(f"     - {key}", flush=True)
            else:
                print(f"   'properties' is not a dictionary, but type: {type(properties)}", flush=True)
            
            # Proviamo a stampare l'albero completo dei parametri
            try:
                revit_parameters = properties['Parameters']
                print("     - Parameters:", flush=True)
                instance_params = revit_parameters['Instance Parameters']
                print("       - Instance Parameters:", flush=True)
                for group_name, group_content in instance_params.items():
                    print(f"         - Group: {group_name}", flush=True)
                    for param_name in group_content.keys():
                        print(f"           - Param: {param_name}", flush=True)
            except (KeyError, AttributeError):
                print("     Could not fully inspect the parameter tree.", flush=True)

            print("   ----------------------------------", flush=True)
            # Usciamo dopo aver ispezionato la prima apertura.
            return []

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
