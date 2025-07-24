# main.py
# Versione funzionante della Regola #1: Censimento Antincendio.
# Utilizza la struttura dati e i nomi dei parametri corretti scoperti tramite il debug.

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
    Esegue la Regola #1: Verifica che tutti i muri e solai abbiano
    il parametro 'Fire_Rating' compilato.
    """
    print("--- STARTING RULE #1: FIRE RATING CENSUS ---", flush=True)
    
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
                
                try:
                    # Seguiamo il percorso esatto che abbiamo scoperto.
                    properties = getattr(el, 'properties')
                    revit_parameters = properties['Parameters']
                    instance_params = revit_parameters['Instance Parameters']
                    text_group = instance_params[PARAMETER_GROUP]
                    fire_rating_param = text_group[FIRE_RATING_PARAM]
                    
                    value = getattr(fire_rating_param, 'value', None)
                    if value is None or not str(value).strip():
                        raise ValueError("Parameter value is missing or empty.")

                except (AttributeError, KeyError, ValueError) as e:
                    print(f"ERROR: Element {el.id} failed validation. Reason: {e}", flush=True)
                    validation_errors.append(el)

        print(f"Validation complete. {objects_validated} objects were checked.", flush=True)

        if validation_errors:
            error_message = f"Validation failed: {len(validation_errors)} elements are missing the '{FIRE_RATING_PARAM}' parameter."
            
            ctx.attach_error_to_objects(
                category=f"Missing Data: {FIRE_RATING_PARAM}",
                affected_objects=validation_errors,
                message=f"The parameter '{FIRE_RATING_PARAM}' is missing or empty.",
                visual_overrides={"color": "red"}
            )
            ctx.mark_run_failed(error_message)
        else:
            if objects_validated > 0:
                ctx.mark_run_success("Validation passed: All checked Walls and Floors have the 'FireRating' parameter.")
            else:
                ctx.mark_run_success("Validation complete: No Walls or Floors were found in the commit to validate.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- END OF RULE #1 ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
