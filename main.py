# main.py
# Versione funzionante della Regola #1: Censimento Antincendio.
# Utilizza una ricerca ricorsiva per trovare in modo affidabile tutti gli elementi.

from speckle_automate import AutomationContext, execute_automate_function

# Definiamo i tipi di oggetti che vogliamo controllare in modo più robusto.
TARGET_TYPES = ["Wall", "Floor"]
# Definiamo il nome esatto del parametro che cercheremo.
FIRE_RATING_PARAM = "FireRating"


def find_all_elements(base_object) -> list:
    """
    Cerca ricorsivamente in un oggetto Speckle tutti gli elementi,
    indipendentemente da quanto sono annidati in liste o collezioni.
    """
    all_elements = []

    # Se l'oggetto ha una proprietà 'elements', esplorala.
    if hasattr(base_object, "elements") and base_object.elements is not None:
        for element in base_object.elements:
            all_elements.extend(find_all_elements(element))
    
    # Se l'oggetto stesso non è una collezione, aggiungilo alla lista.
    # Questo cattura gli elementi finali (muri, solai, etc.).
    elif "Collection" not in getattr(base_object, "speckle_type", ""):
        all_elements.append(base_object)
        
    return all_elements


def main(ctx: AutomationContext) -> None:
    """
    Esegue la Regola #1: Verifica che tutti i muri e solai abbiano
    il parametro 'FireRating' compilato.
    """
    print("--- AVVIO REGOLA #1: CENSIMENTO ANTINCENDIO ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        
        # Usiamo la nuova funzione ricorsiva per trovare TUTTI gli elementi.
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("Nessun elemento Revit trovato nel commit.")
            return

        print(f"Trovati {len(all_elements)} elementi totali da analizzare.", flush=True)

        validation_errors = []
        objects_validated = 0
        for el in all_elements:
            speckle_type = getattr(el, 'speckle_type', '')
            
            # Controlliamo solo i tipi che ci interessano (Muri e Solai)
            if any(target in speckle_type for target in TARGET_TYPES):
                objects_validated += 1
                print(f"-> Elemento {el.id} ({speckle_type}) identificato come target. Procedo con la validazione.", flush=True)
                
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
            )
            ctx.mark_run_failed(error_message)
        else:
            if objects_validated > 0:
                ctx.mark_run_success("Validazione superata: Tutti i muri e solai controllati hanno il parametro 'FireRating' compilato.")
            else:
                ctx.mark_run_success("Validazione completata: Nessun muro o solaio trovato nel commit da validare.")

    except Exception as e:
        error_message = f"Errore durante l'esecuzione dello script: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- FINE REGOLA #1 ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
