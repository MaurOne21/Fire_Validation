# main.py
# Versione con logging e ispezione degli oggetti migliorati per il debug.

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
    print("--------------------------------------------------")
    print("SPECKLE AUTOMATE SCRIPT ESEGUITO CORRETTAMENTE")
    print(f"Stream ID: {ctx.stream_id}")
    print(f"Commit ID: {ctx.version_id}")
    print("--------------------------------------------------")
    
    print("Automazione avviata: Esecuzione Regola #1 - Censimento Antincendio.")

    commit_root_object = ctx.get_commit_root()
    objects_to_check = find_objects_by_type(commit_root_object, TARGET_TYPES)
    print(f"Trovati {len(objects_to_check)} muri e solai da controllare.")

    if not objects_to_check:
        ctx.mark_run_succeeded("Nessun muro o solaio trovato nel commit. Controllo non necessario.")
        print("Nessun oggetto target trovato. Uscita.")
        return

    validation_errors = check_fire_rating_parameter(objects_to_check)

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
    
    # --- BLOCCO DI ISPEZIONE OGGETTO ---
    # Stampiamo le proprietà del primo oggetto trovato per ispezionare la sua struttura.
    if objects:
        first_obj = objects[0]
        print("\n--- ISPEZIONE DEL PRIMO OGGETTO TROVATO ---")
        print(f"ID Oggetto: {getattr(first_obj, 'id', 'N/A')}")
        print(f"Speckle Type: {getattr(first_obj, 'speckle_type', 'N/A')}")
        print("Proprietà disponibili:")
        for prop in first_obj.get_member_names():
            try:
                value = getattr(first_obj, prop)
                # Stampa solo valori semplici per non intasare i log
                if isinstance(value, (str, int, float, bool)) or value is None:
                    print(f"  - {prop}: {value}")
            except:
                continue
        print("-----------------------------------------\n")

    for obj in objects:
        fire_rating_value = obj.get(FIRE_RATING_PARAM)

        # La validazione fallisce se il parametro non esiste (None)
        # o se è una stringa vuota o contiene solo spazi.
        if fire_rating_value is None or not str(fire_rating_value).strip():
            print(f"ERRORE: L'elemento {obj.id} non ha un {FIRE_RATING_PARAM} valido.")
            elements_with_errors.append(obj.id)
            
    return elements_with_errors
