# main.py
# Script di diagnosi definitiva per ispezionare la struttura dell'oggetto parametro.

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
    Esegue una diagnosi finale per ispezionare l'oggetto parametro 'Fire_Rating'.
    """
    print("--- STARTING FINAL PARAMETER DIAGNOSTIC SCRIPT ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("No Revit elements found in the commit.")
            return

        print(f"Found {len(all_elements)} total elements to analyze.", flush=True)

        for el in all_elements:
            category = getattr(el, 'category', '')
            
            if any(target.lower() in category.lower() for target in TARGET_CATEGORIES):
                print(f"\n-> Found target element {el.id} (Category: {category})", flush=True)
                
                try:
                    # Seguiamo il percorso esatto che abbiamo scoperto.
                    properties = getattr(el, 'properties')
                    revit_parameters = properties['Parameters']
                    instance_params = revit_parameters['Instance Parameters']
                    text_group = instance_params[PARAMETER_GROUP]
                    fire_rating_param_object = text_group[FIRE_RATING_PARAM]
                    
                    print(f"   SUCCESS: Found '{FIRE_RATING_PARAM}' parameter object.", flush=True)
                    print("   --- INSPECTING THE PARAMETER OBJECT ---", flush=True)
                    print(f"   Parameter Object Type: {type(fire_rating_param_object)}", flush=True)
                    print("   Available attributes and methods:", flush=True)
                    
                    # Usiamo dir() per ottenere una "radiografia" completa dell'oggetto.
                    for attr in dir(fire_rating_param_object):
                        print(f"     - {attr}", flush=True)

                    # Proviamo a vedere se ha un attributo 'value' e stampiamolo.
                    final_value = getattr(fire_rating_param_object, 'value', "ATTRIBUTE 'value' NOT FOUND")
                    print(f"   Attempting to get '.value': {final_value}", flush=True)
                    print("   --------------------------------------", flush=True)

                    # Usciamo dopo aver ispezionato il primo oggetto per mantenere i log puliti.
                    break

                except (AttributeError, KeyError) as e:
                    print(f"   DIAGNOSTIC FAILED for element {el.id}: Could not find the parameter. Reason: {e}", flush=True)
                    continue

        ctx.mark_run_success("Diagnostic complete. Check logs for the parameter object structure.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- END OF FINAL DIAGNOSTIC SCRIPT ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
