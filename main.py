# main.py
# Versione funzionante della Regola #1: Censimento Antincendio.
# Aggiunto logging per il tipo di oggetto per il debug finale.

from speckle_automate import AutomationContext, execute_automate_function

# Definiamo i tipi di oggetti che vogliamo controllare in modo più robusto.
TARGET_TYPES = ["Wall", "Floor"]
# Definiamo il nome esatto del parametro che cercheremo.
FIRE_RATING_PARAM = "FireRating"


def main(ctx: AutomationContext) -> None:
    """
    Esegue la Regola #1: Verifica che tutti i muri e solai abbiano
    il parametro 'FireRating' compilato.
    """
    print("--- AVVIO REGOLA #1: CENSIMENTO ANTINCENDIO ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        
        # --- NUOVO METODO DI RICERCA ELEMENTI ---
        # I commit da Revit hanno una struttura annidata. Scaviamo per trovare gli elementi.
        all_elements = []
        
        # Il primo livello di solito ha una proprietà 'elements' o '@elements'.
        top_level_elements = getattr(commit_root_object, 'elements', None)
        if not top_level_elements:
            top_level_elements = getattr(commit_root_object, '@elements', [])

        # Iteriamo attraverso le collezioni di categorie (es. "Muri", "Solai")
        for category_collection in top_level_elements:
            # Ogni collezione di categoria ha a sua volta una lista 'elements'.
            elements_in_category = getattr(category_collection, 'elements', None)
            if not elements_in_category:
                elements_in_category = getattr(category_collection, '@elements', [])
            
            if elements_in_category:
                all_elements.extend(elements_in_category)
        
        # --- FINE NUOVO METODO ---

        if not all_elements:
            ctx.mark_run_success("Nessun elemento Revit trovato nel commit.")
            return

        print(f"Trovati {len(all_elements)} elementi totali da analizzare.", flush=True)

        validation_errors = []
        objects_validated = 0
        for el in all_elements:
            speckle_type = getattr(el, 'speckle_type', '')
            # Aggiungiamo un print per vedere il tipo esatto di ogni oggetto.
            print(f"Analizzando elemento ID {el.id} con tipo: {speckle_type}", flush=True)
            
            # Controlliamo solo i tipi che ci interessano (Muri e Solai)
            if any(target.lower() in speckle_type.lower() for target in TARGET_TYPES):
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
