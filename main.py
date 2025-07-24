# main.py
# Script di ispezione finale per stampare l' "albero" dei parametri
# all'interno dell'oggetto 'properties', trattandolo come un dizionario.

from speckle_automate import AutomationContext, execute_automate_function

# Definiamo le CATEGORIE di Revit che vogliamo controllare.
TARGET_CATEGORIES = ["Muri", "Pavimenti"]

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
    Esegue un'ispezione finale per capire la struttura dei parametri.
    """
    print("--- AVVIO ISPEZIONE FINALE DEI PARAMETRI ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("Nessun elemento Revit trovato nel commit.")
            return

        print(f"Trovati {len(all_elements)} elementi totali da analizzare.", flush=True)

        for el in all_elements:
            category = getattr(el, 'category', '')
            
            if any(target.lower() in category.lower() for target in TARGET_CATEGORIES):
                print(f"-> Trovato un oggetto target (Categoria: {category}). Ispeziono le sue 'properties'.", flush=True)
                
                properties = getattr(el, 'properties', None)
                if not properties:
                    print("   ERRORE: Questo oggetto non ha 'properties'.", flush=True)
                    continue

                print("   --- Contenuto di 'properties' ---", flush=True)
                # --- SOLUZIONE APPLICATA QUI ---
                # Trattiamo 'properties' come un dizionario Python.
                if isinstance(properties, dict):
                    for key in properties.keys():
                        print(f"     - {key}", flush=True)
                else:
                    print(f"   L'oggetto 'properties' non è un dizionario, ma di tipo: {type(properties)}", flush=True)
                print("   ---------------------------------", flush=True)
                
                # Usciamo dopo aver ispezionato il primo oggetto per mantenere i log puliti.
                break 

        ctx.mark_run_success("Ispezione completata. Controllare i log per l'albero dei parametri.")

    except Exception as e:
        error_message = f"Errore durante l'esecuzione dello script: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- FINE ISPEZIONE FINALE ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
