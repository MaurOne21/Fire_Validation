# main.py
# Script di diagnosi definitiva per tracciare il percorso di accesso ai parametri.

from speckle_automate import AutomationContext, execute_automate_function

# Definiamo le CATEGORIE di Revit che vogliamo controllare.
TARGET_CATEGORIES = ["Muri", "Pavimenti"]
# Definiamo il nome esatto del parametro che cercheremo.
FIRE_RATING_PARAM = "Fire_Rating"
# Definiamo il gruppo in cui si trova il parametro.
PARAMETER_GROUP = "Testo"


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


def main(ctx: AutomationContext) -> None:
    """
    Esegue una diagnosi passo-passo per tracciare il percorso di accesso
    al parametro 'Fire_Rating'.
    """
    print("--- STARTING FINAL DIAGNOSTIC SCRIPT ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("No Revit elements found in the commit.")
            return

        print(f"Found {len(all_elements)} total elements to analyze.", flush=True)

        validation_errors = []
        objects_validated = 0
        for el in all_elements:
            category = getattr(el, 'category', '')
            
            if any(target.lower() in category.lower() for target in TARGET_CATEGORIES):
                objects_validated += 1
                print(f"\n-> Validating element {el.id} (Category: {category})", flush=True)
                
                try:
                    # Step 1: Trova 'properties'
                    properties = getattr(el, 'properties', None)
                    if not properties: raise ValueError("'properties' object not found")
                    print("   Step 1: 'properties' object found.", flush=True)

                    # Step 2: Trova 'Parameters' dentro 'properties'
                    revit_parameters = properties.get('Parameters')
                    if not revit_parameters: raise ValueError("'Parameters' object not found inside 'properties'")
                    print("   Step 2: 'Parameters' object found.", flush=True)

                    # Step 3: Trova 'Instance Parameters' dentro 'Parameters'
                    instance_params_group = revit_parameters.get('Instance Parameters')
                    if not instance_params_group: raise ValueError("'Instance Parameters' object not found inside 'Parameters'")
                    print("   Step 3: 'Instance Parameters' object found.", flush=True)
                    
                    # Step 4: Trova il gruppo 'Testo' dentro 'Instance Parameters'
                    text_group = instance_params_group.get(PARAMETER_GROUP)
                    if not text_group: raise ValueError(f"'{PARAMETER_GROUP}' group not found inside 'Instance Parameters'")
                    print(f"   Step 4: '{PARAMETER_GROUP}' group found.", flush=True)

                    # Step 5: Trova il parametro 'Fire_Rating' dentro il gruppo 'Testo'
                    fire_rating_param = text_group.get(FIRE_RATING_PARAM)
                    if not fire_rating_param: raise ValueError(f"'{FIRE_RATING_PARAM}' not found inside '{PARAMETER_GROUP}' group")
                    print(f"   Step 5: '{FIRE_RATING_PARAM}' object found.", flush=True)
                    
                    # Step 6: Controlla il valore del parametro
                    value = getattr(fire_rating_param, 'value', None)
                    if value is None: raise ValueError("Parameter exists, but its 'value' is None or missing.")
                    print(f"   Step 6: SUCCESS! Found value: '{value}'", flush=True)

                except ValueError as e:
                    print(f"   DIAGNOSTIC FAILED for element {el.id}: {e}", flush=True)
                    validation_errors.append(el)

        print(f"\nDiagnostic complete. {objects_validated} objects were checked.", flush=True)

        if validation_errors:
            ctx.mark_run_failed("Diagnostic failed. Check logs for details.")
        else:
            ctx.mark_run_success("Diagnostic successful. All parameters were found.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- END OF FINAL DIAGNOSTIC SCRIPT ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
