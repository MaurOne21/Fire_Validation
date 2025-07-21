# main.py
# Versione con logging migliorato per il debug.

from speckle_automate import (
    AutomationContext,
)

# Definiamo i tipi di oggetti che vogliamo controllare.
TARGET_TYPES = ["Objects.BuiltElements.Wall", "Objects.BuiltElements.Floor"]
# Definiamo il nome esatto del parametro che cercheremo.
FIRE_RATING_PARAM = "FireRating"


def find_objects_by_type(base_object, target_types: list) -> list:
    """
    Cerca ricorsivamente in un oggetto Speckle tutti gli elementi
    che corrispondono ai tipi specificati.
    """
    found_objects = []
    
    if getattr(base_object, "speckle_type", None) in target_types:
        found_objects.append(base_object)

    for member_name in base_object.get_member_names():
        try:
            member_value = getattr(base_object, member_name)
        except:
            continue

        if isinstance(member_value, list):
            for item in member_value:
                if isinstance(item, (dict, object)) and hasattr(item, "get_member_names"):
                    found_objects.extend(find_objects_by_type(item, target_types))
        elif isinstance(member_value, (dict, object)) and hasattr(member_value, "get_member_names"):
            found_objects.extend(find_objects_by_type(member_value, target_types))
            
    return found_objects


def main(ctx: AutomationContext) -> None:
    """
    Questa è la funzione principale che Speckle eseguirà ad ogni commit.
    """
    # --- NUOVO BLOCCO DI DEBUG ---
    # Questi print ci aiuteranno a capire se lo script viene eseguito correttamente.
    print("--------------------------------------------------")
    print("SPECKLE AUTOMATE SCRIPT ESEGUITO CORRETTAMENTE")
    print(f"Stream ID: {ctx.stream_id}")
    print(f"Commit ID: {ctx.version_id}")
    print("--------------------------------------------------")
    
    print("Automazione avviata: Esecuzione Regola #1 - Censimento Antincendio.")

    # 1. Otteniamo il modello dal commit che ha attivato l'automazione.
    commit_root_object = ctx.get_commit_root()

    # 2. Usiamo la nostra nuova funzione per trovare tutti gli oggetti dei tipi
    #    che ci interessano (muri e solai) nel modello.
    objects_to_check = find_objects_by_type(commit_root_object, TARGET_TYPES)
    print(f"Trovati {len(objects_to_check)} muri e solai da controllare.")

    # --- NUOVO CONTROLLO ---
    # Se non troviamo nessun oggetto, terminiamo con successo.
    if not objects_to_check:
        ctx.mark_run_succeeded("Nessun muro o solaio trovato nel commit. Controllo non necessario.")
        print("Nessun oggetto target trovato. Uscita.")
        return

    # 3. Chiamiamo la nostra funzione di validazione.
    validation_errors = check_fire_rating_parameter(objects_to_check)

    # 4. In base al risultato, decidiamo se l'automazione è passata o fallita.
    if validation_errors:
        error_message = f"Validazione fallita: {len(validation_errors)} elementi non hanno il parametro '{FIRE_RATING_PARAM}' compilato."
        
        ctx.attach_error_to_objects(
            category=f"Validazione Dati: {FIRE_RATING_PARAM}",
            object_ids=validation_errors,
            message=f"Il parametro '{FIRE_RATING_PARAM}' è mancante o vuoto.",
        )
        
        ctx.mark_run_failed(error_message)
        print(error_message)

    else:
        success_message = "Validazione superata: Tutti i muri e solai hanno il parametro 'FireRating' compilato."
        ctx.mark_run_succeeded(success_message)
        print(success_message)

    print("Automazione completata.")


def check_fire_rating_parameter(objects: list) -> list[str]:
    """
    Controlla una lista di oggetti Speckle per verificare la presenza
    e la compilazione del parametro 'FireRating'.
    """
    elements_with_errors = []
    for obj in objects:
        fire_rating_value = obj.get(FIRE_RATING_PARAM)

        if fire_rating_value is None or fire_rating_value == "":
            print(f"ERRORE: L'elemento {obj.id} non ha un {FIRE_RATING_PARAM} valido.")
            elements_with_errors.append(obj.id)
            
    return elements_with_errors
