# main.py
# Versione funzionante con la Regola #1 (Censimento Antincendio)
# e la Regola #2 (Workflow di Approvazione Demolizioni).

from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
# --- Regola #1 ---
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti"]
FIRE_RATING_PARAM = "Fire_Rating"
PARAMETER_GROUP = "Testo"

# --- Regola #2 ---
# NOTA: Sostituisci questo con l'ID reale del tuo stream strutturale!
STRUCTURAL_STREAM_ID = "d48a1d3b3c" 
# NOTA: Questo deve corrispondere al nome del parametro in Revit
PHASE_DEMOLISHED_PARAM = "Fase di demolizione"
# Categorie strutturali da considerare portanti
STRUCTURAL_CATEGORIES = ["Muri", "Pilastri", "Travi", "Structural Framing", "Structural Columns"]
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


#============== LOGICA DELLA REGOLA #1 ===============================================
def run_fire_rating_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #1: Verifica che tutti i muri e solai abbiano
    il parametro 'Fire_Rating' compilato.
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
                text_group = instance_params[PARAMETER_GROUP]
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


#============== LOGICA DELLA REGOLA #2 (NUOVA!) ======================================
def run_demolition_check(all_elements: list, ctx: AutomationContext) -> list:
    """
    Esegue la Regola #2: Controlla se un elemento in fase di demolizione
    interseca un elemento portante.
    """
    print("--- RUNNING RULE #2: DEMOLITION APPROVAL WORKFLOW ---", flush=True)
    
    # 1. Otteniamo il modello strutturale più recente.
    try:
        # --- SOLUZIONE APPLICATA QUI ---
        # La funzione get_model prende solo l'ID del modello.
        # Di default, carica l'ultima versione del branch principale ("main").
        structural_root_object = ctx.get_model(STRUCTURAL_STREAM_ID)
        structural_elements = find_all_elements(structural_root_object)
        print(f"Successfully loaded {len(structural_elements)} elements from the structural model.", flush=True)
    except Exception as e:
        print(f"ERROR (Rule 2): Could not load the structural model. Reason: {e}", flush=True)
        return [] # Non possiamo procedere se non carichiamo il modello strutturale.

    # 2. Filtriamo gli elementi strutturali per trovare solo quelli portanti.
    load_bearing_elements = []
    for el in structural_elements:
        category = getattr(el, 'category', '')
        if any(target.lower() in category.lower() for target in STRUCTURAL_CATEGORIES):
            load_bearing_elements.append(el)
    
    print(f"Found {len(load_bearing_elements)} load-bearing elements.", flush=True)

    # 3. Troviamo gli elementi architettonici in fase di demolizione.
    demolished_elements = []
    for el in all_elements:
        try:
            properties = getattr(el, 'properties')
            revit_parameters = properties['Parameters']
            instance_params = revit_parameters['Instance Parameters']
            fasi_group = instance_params.get("Fasi", {})
            phase_demolished = fasi_group.get(PHASE_DEMOLISHED_PARAM, {})
            
            # Se un elemento è demolito, il suo valore non è "Nessuno"
            if phase_demolished.get("value") and phase_demolished.get("value") != "Nessuno":
                demolished_elements.append(el)
        except (AttributeError, KeyError):
            continue
    
    print(f"Found {len(demolished_elements)} demolished elements in the current commit.", flush=True)

    # 4. Per ora, ci limitiamo a segnalare gli elementi demoliti.
    #    Il controllo di intersezione geometrica è un passo successivo più complesso.
    if demolished_elements:
        ctx.attach_warning_to_objects(
            category="Structural Demolition Review",
            affected_objects=demolished_elements,
            message="This element is set to be demolished. Please ensure this does not affect a load-bearing element.",
            visual_overrides={"color": "orange"}
        )
    
    print(f"Rule #2 Finished. {len(demolished_elements)} demolished elements found.", flush=True)
    return [] # Per ora, questa regola genera solo un avviso, non un errore che fa fallire la Run.


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

        # Eseguiamo tutte le nostre regole di validazione
        all_errors = []
        all_errors.extend(run_fire_rating_check(all_elements, ctx))
        all_errors.extend(run_demolition_check(all_elements, ctx))
        
        # Se alla fine ci sono errori da una qualsiasi delle regole, falliamo la Run.
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
