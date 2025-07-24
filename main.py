# main.py
# Versione funzionante della Regola #1: Censimento Antincendio.
# Corretto il metodo di identificazione del tipo di oggetto.

from speckle_automate import AutomationContext, execute_automate_function

# Definiamo i tipi di oggetti che vogliamo controllare in modo più robusto.
TARGET_TYPES = ["Wall", "Floor"]
# Definiamo il nome esatto del parametro che cercheremo.
FIRE_RATING_PARAM = "FireRating"


def find_revit_elements_in_commit(commit_root_object) -> list:
    """
    Naviga la struttura del commit per trovare la lista di elementi Revit.
    I commit da Revit hanno spesso una struttura annidata di Collezioni.
    """
    print("Inizio ricerca elementi Revit nel commit...", flush=True)
    
    if hasattr(commit_root_object, "elements"):
        for category_collection in commit_root_object.elements:
            if hasattr(category_collection, "elements"):
                print(f"Trovata categoria: {getattr(category_collection, 'name', 'N/A')}", flush=True)
                return category_collection.elements
    
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
        elements_to_check = find_revit_elements_in_commit(commit_root_object)

        if not elements_to_check:
            ctx.mark_run_success("Nessun elemento Revit trovato nel commit.")
            return

        print(f"Trovati {len(elements_to_check)} elementi totali da analizzare.", flush=True)

        validation_errors = []
        objects_validated = 0
        for el in elements_to_check:
            speckle_type = getattr(el, 'speckle_type', '')
            print(f"Analizzando elemento ID {el.id} con tipo: {speckle_type}", flush=True)

            # Controlliamo solo i tipi che ci interessano (Muri e Solai)
            if any(target in speckle_type for target in TARGET_TYPES):
                objects_validated += 1
                print(f"-> Elemento {el.id} identificato come target. Procedo con la validazione.", flush=True)
                
                parameters = getattr(el, 'parameters', None)
                if not parameters:
                    print(f"ERRORE: L'elemento {el.id} non ha un oggetto 'parameters'.", flush=True)
                    validation_errors.append(el.id)
                    continue

                fire_rating_param = parameters.get(FIRE_RATING_PARAM)
                
                if not fire_rating_param or not getattr(fire_rating_param, 'value', None):
                    print(f"ERRORE: L'elemento {el.id} non ha un '{FIRE_RATING_PARAM}' valido.", flush=True)
                    validation_errors.append(el.id)

        print(f"Validazione completata. {objects_validated} oggetti sono stati controllati.", flush=True)

        if validation_errors:
            error_message = f"Validazione fallita: {len(validation_errors)} elementi non hanno il parametro '{FIRE_RATING_PARAM}' compilato."
            ctx.attach_error_to_objects(
                category=f"Dati Mancanti: {FIRE_RATING_PARAM}",
                object_ids=validation_errors,
                message=f"Il parametro '{FIRE_RATING_PARAM}' è mancante o vuoto.",
          
