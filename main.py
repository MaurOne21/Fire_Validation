# main.py
# Fully functional version with Rule #1 (Fire Rating Census)
# and Rule #3 (Compartmentation Integrity), with the final correct logic.

from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
# --- Rule #1 ---
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti"]
FIRE_RATING_PARAM = "Fire_Rating"
PARAMETER_GROUP_RULE_1 = "Testo"

# --- Rule #3 ---
OPENING_CATEGORIES = ["Porte", "Finestre"] 
FIRE_SEAL_PARAM = "Sigillatura_Rei_Installation"
PARAMETER_GROUP_RULE_3 = "Altro"
#=====================================================================================


def find_all_elements(base_object) -> list:
    """
    Recursively searches a Speckle object for all elements.
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
    Executes Rule #1: Verifies that all Walls and Floors
    have the 'Fire_Rating' parameter filled out.
    """
    print("--- RUNNING RULE #1: FIRE RATING CENSUS ---", flush=True)
    
    validation_errors = []
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in TARGET_CATEGORIES_RULE_1):
            try:
                properties = getattr(el, 'properties')
                revit_parameters = properties['Parameters']
                instance_params = revit_parameters['Instance Parameters']
                text_group = instance_params[PARAMETER_GROUP_RULE_1]
                fire_rating_param_dict = text_group[FIRE_RATING_PARAM]
                value = fire_rating_param_dict.get("value")
                if value is None or not str(value).strip():
                    raise ValueError("Parameter value is missing or empty.")
            except (AttributeError, KeyError, ValueError) as e:
                print(f"ERROR (Rule 1): Element {el.id} failed validation. Reason: {e}", flush=True)
                validation_errors.append(el)

    if validation_errors:
        ctx.attach_error_to_objects(
            category=f"Missing Data: {FIRE_RATING_PARAM}",
            affected_objects=validation_errors,
            message=f"The parameter '{FIRE_RATING_PARAM}' is missing or empty.",
            visual_overrides={"color": "red"}
        )
    
    print(f"Rule #1 Finished. {len(validation_errors)} errors found.", flush=True)
    return validation_errors


#============== LOGICA DELLA REGOLA #3 (CORRETTA) ======================================
def run_penetration_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Executes Rule #3: Checks that all doors/windows in fire-rated walls
    have the specified fire sealing.
    """
    print("--- RUNNING RULE #3: FIRE COMPARTMENTATION CHECK ---", flush=True)
    
    # For this demo, we assume that if there are fire-rated walls, all doors must be checked.
    
    penetration_errors = []
    # Search for doors/windows throughout the model
    for el in all_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in OPENING_CATEGORIES):
            try:
                # --- FINAL SOLUTION APPLIED HERE ---
                # We search for the parameter in the correct path: properties -> Parameters -> Instance Parameters -> Altro
                properties = getattr(el, 'properties')
                revit_parameters = properties['Parameters']
                instance_params = revit_parameters['Instance Parameters']
                other_group = instance_params[PARAMETER_GROUP_RULE_3]
                seal_param_dict = other_group[FIRE_SEAL_PARAM]
                
                # A Yes/No parameter in Revit is translated to a boolean True/False in Python.
                # The condition 'if not value' catches both the case where the value is False,
                # and the case where the parameter is missing (None).
                value = seal_param_dict.get("value")
                if not value: 
                    raise ValueError("Fire seal parameter is missing or set to 'No'.")

            except (AttributeError, KeyError, ValueError) as e:
                print(f"ERROR (Rule 3): Opening {el.id} failed validation. Reason: {e}", flush=True)
                penetration_errors.append(el)

    if penetration_errors:
        ctx.attach_error_to_objects(
            category="Unsealed Fire Penetration",
            affected_objects=penetration_errors,
            message=f"This opening in a fire-rated wall is missing the '{FIRE_SEAL_PARAM}' parameter.",
            visual_overrides={"color": "#FF8C00"} # Dark Orange
        )
    
    print(f"Rule #3 Finished. {len(penetration_errors)} errors found.", flush=True)
    return penetration_errors


#============== ORCHESTRATORE PRINCIPALE =============================================
def main(ctx: AutomationContext) -> None:
    """
    Main function that orchestrates the execution of all validation rules.
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
        all_errors.extend(run_penetration_check(all_elements, ctx))
        
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
