# main.py
# Versione funzionante della Regola #1: Censimento Antincendio.
# Lo script ora è in grado di navigare la struttura dati annidata di Revit.

from speckle_automate import AutomationContext, execute_automate_function

# Definiamo i tipi di oggetti che vogliamo controllare.
TARGET_TYPES = ["Objects.BuiltElements.Wall:Objects.BuiltElements.Revit.RevitWall", "Objects.BuiltElements.Floor:Objects.BuiltElements.Revit.RevitFloor"]
# Definiamo il nome esatto del parametro che cercheremo.
FIRE_RATING_PARAM = "FireRating"


def find_revit_elements_in_commit(commit_root_object) -> list:
    """
    Naviga la struttura del commit per trovare la lista di elementi Revit.
    I commit da Revit hanno spesso una struttura annidata di Collezioni.
    """
    print("Inizio ricerca elementi Revit nel commit...", flush=True)
    
    # Controlla se l'oggetto radice ha una lista 'elements'.
    if hasattr(commit_root_object, "elements"):
        # Itera attraverso le collezioni annidate (es. Categorie di Revit)
        for category_collection in commit_root_object.elements:
            if hasattr(category_collection, "elements"):
                print(f"Trovata categoria: {getattr(category_collection, 'name', 'N/A')}", flush=True)
                return category_collection.elements # Restituisce la prima lista di elementi trovata
    
    print("ATTENZIONE: Nessuna lista di elementi trovata nella struttura attesa.", flush=True)
    return []


def main(ctx: AutomationContext) -> None:
    """
    Esegue la Regola #1: Verifica che tutti i muri e solai abbiano
    il parametro 'FireRating' compilato.
    """
    print("--- AVVIO REGOLA #1: CENSIMENTO ANTINCENDIO ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        
        # Usiamo la nuova funzione per trovare la lista corretta di elementi.
        elements_to_check = find_revit_elements_in_commit(commit_root_object)

        if not elements_to_check:
            ctx.mark_run_success("Nessun elemento Revit trovato nel commit.")
            return

        print(f"Trovati {len(elements_to_check)} elementi da analizzare.", flush=True)

        validation_errors = []
        for el in elements_to_check:
            # Controlliamo solo i tipi che ci interessano (Muri e Solai)
            speckle_type = getattr(el, 'speckle_type', '')
            if any(target in speckle_type for target in TARGET_TYPES):
                
                # I parametri di istanza sono spesso in un sotto-oggetto 'parameters'
                parameters = getattr(el, 'parameters', None)
                if not parameters:
                    print(f"ERRORE: L'elemento {el.id} non ha un oggetto 'parameters'.", flush=True)
                    validation_errors.append(el.id)
                    continue

                fire_rating_param = parameters.get(FIRE_RATING_PARAM)
                
                # Il parametro stesso è un oggetto, il valore è in 'value'
                if not fire_rating_param or not getattr(fire_rating_param, 'value', None):
                    print(f"ERRORE: L'elemento {el.id} non ha un '{FIRE_RATING_PARAM}' valido.", flush=True)
                    validation_errors.append(el.id)

        if validation_errors:
            error_message = f"Validazione fallita: {len(validation_errors)} elementi non hanno il parametro '{FIRE_RATING_PARAM}' compilato."
            ctx.attach_error_to_objects(
                category=f"Dati Mancanti: {FIRE_RATING_PARAM}",
                object_ids=validation_errors,
                message=f"Il parametro '{FIRE_RATING_PARAM}' è mancante o vuoto.",
            )
            ctx.mark_run_failed(error_message)
        else:
            ctx.mark_run_success("Validazione superata: Tutti i muri e solai hanno il parametro 'FireRating' compilato.")

    except Exception as e:
        error_message = f"Errore durante l'esecuzione dello script: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- FINE REGOLA #1 ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
