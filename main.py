# main.py
# Versione corretta dello script per la Regola #1: Il Censimento Antincendio.

from speckle_automate import (
    AutomationContext,
    automation_run, # NOTA: 'execute_automation' è stato rimosso da questo import.
)
from speckle_automate.helpers import get_speckle_objects_from_commit_by_type

# Definiamo i tipi di oggetti che vogliamo controllare.
# Questi sono i tipi standard di Speckle per muri e solai.
TARGET_TYPES = ["Objects.BuiltElements.Wall", "Objects.BuiltElements.Floor"]
# Definiamo il nome esatto del parametro che cercheremo.
FIRE_RATING_PARAM = "FireRating"


@automation_run
def run_function(ctx: AutomationContext) -> None:
    """
    Questa è la funzione principale che Speckle eseguirà ad ogni commit
    sullo stream a cui collegheremo questa automazione.
    """
    print("Automazione avviata: Esecuzione Regola #1 - Censimento Antincendio.")

    # 1. Otteniamo il modello dal commit che ha attivato l'automazione.
    commit_root_object = ctx.get_commit_root()

    # 2. Usiamo una funzione di supporto per trovare tutti gli oggetti dei tipi
    #    che ci interessano (muri e solai) nel modello.
    objects_to_check = get_speckle_objects_from_commit_by_type(
        commit_root_object, TARGET_TYPES
    )
    print(f"Trovati {len(objects_to_check)} muri e solai da controllare.")

    # 3. Chiamiamo la nostra funzione di validazione.
    validation_errors = check_fire_rating_parameter(objects_to_check)

    # 4. In base al risultato, decidiamo se l'automazione è passata o fallita.
    if validation_errors:
        # Se ci sono errori, l'automazione fallisce.
        # Creiamo un messaggio di errore chiaro che elenca gli ID degli elementi problematici.
        error_message = f"Validazione fallita: {len(validation_errors)} elementi non hanno il parametro '{FIRE_RATING_PARAM}' compilato."
        
        # Aggiungiamo gli ID degli elementi all'errore per una facile identificazione.
        ctx.attach_error_to_objects(
            category=f"Validazione Dati: {FIRE_RATING_PARAM}",
            object_ids=validation_errors,
            message=f"Il parametro '{FIRE_RATING_PARAM}' è mancante o vuoto.",
        )
        
        ctx.mark_run_failed(error_message)
        print(error_message)

    else:
        # Se non ci sono errori, l'automazione ha successo!
        success_message = "Validazione superata: Tutti i muri e solai hanno il parametro 'FireRating' compilato."
        ctx.mark_run_succeeded(success_message)
        print(success_message)

    print("Automazione completata.")


def check_fire_rating_parameter(objects: list) -> list[str]:
    """
    Controlla una lista di oggetti Speckle per verificare la presenza
    e la compilazione del parametro 'FireRating'.

    Args:
        objects: Una lista di oggetti Speckle da controllare.

    Returns:
        Una lista di ID degli oggetti che non superano la validazione.
    """
    elements_with_errors = []
    for obj in objects:
        # Controlliamo se il parametro esiste nell'oggetto.
        # Usiamo .get() per evitare errori se il parametro non esiste.
        fire_rating_value = obj.get(FIRE_RATING_PARAM)

        # La validazione fallisce se il parametro non esiste (None)
        # o se è una stringa vuota ("").
        if fire_rating_value is None or fire_rating_value == "":
            print(f"ERRORE: L'elemento {obj.id} non ha un {FIRE_RATING_PARAM} valido.")
            elements_with_errors.append(obj.id)
            
    return elements_with_errors

# NOTA: La parte 'if __name__ == "__main__"' è stata rimossa perché causava l'errore.
# Non è necessaria per la pubblicazione della funzione su Speckle.
