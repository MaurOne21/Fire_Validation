# main.py
# Script di diagnosi definitiva per scoprire i nomi dei branch di un modello.

from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE GLOBALE ===============================================
# --- Regola #1 ---
TARGET_CATEGORIES_RULE_1 = ["Muri", "Pavimenti"]
FIRE_RATING_PARAM = "Fire_Rating"
PARAMETER_GROUP = "Testo"

# --- Regola #2 (Diagnosi) ---
# NOTA: Sostituisci questo con l'ID reale del tuo stream strutturale!
STRUCTURAL_STREAM_ID = "d48a1d3b3c" 
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


#============== DIAGNOSI PER LA REGOLA #2 ===========================================
def run_branch_diagnostic(ctx: AutomationContext) -> list:
    """
    Esegue una diagnosi per trovare tutti i nomi dei branch del modello strutturale.
    """
    print("--- RUNNING BRANCH DIAGNOSTIC FOR RULE #2 ---", flush=True)
    
    try:
        # Costruiamo una query GraphQL per ottenere i nomi di tutti i branch.
        query = f"""
            query GetModelBranches {{
              project(id: "{ctx.automation_run_data.project_id}") {{
                model(id: "{STRUCTURAL_STREAM_ID}") {{
                  branches {{
                    items {{
                      name
                    }}
                  }}
                }}
              }}
            }}
        """
        clean_query = " ".join(query.split())
        
        response = ctx.speckle_client.execute_query(query=clean_query)
        
        branches = response["data"]["project"]["model"]["branches"]["items"]
        
        if not branches:
            print("DIAGNOSTIC RESULT: No branches found for the structural model.", flush=True)
        else:
            print("DIAGNOSTIC RESULT: Found the following branches:", flush=True)
            for branch in branches:
                print(f"  - Branch Name: '{branch['name']}'", flush=True)

    except Exception as e:
        print(f"DIAGNOSTIC FAILED: {e}", flush=True)

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

        all_errors = []
        all_errors.extend(run_fire_rating_check(all_elements, ctx))
        # Eseguiamo la nostra funzione di diagnosi invece della regola vera e propria
        run_branch_diagnostic(ctx)
        
        ctx.mark_run_success("Diagnostic complete. Check logs for details.")

    except Exception as e:
        error_message = f"An error occurred during the script execution: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- VALIDATION SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
