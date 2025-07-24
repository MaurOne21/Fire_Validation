# main.py
# Versione funzionante della Regola #1: Censimento Antincendio.
# Corretto il metodo di accesso all'oggetto 'properties'.

from speckle_automate import AutomationContext, execute_automate_function

# Definiamo le CATEGORIE di Revit che vogliamo controllare.
TARGET_CATEGORIES = ["Muri", "Pavimenti"]
# Definiamo il nome esatto del parametro che cercheremo.
FIRE_RATING_PARAM = "FireRating"


def find_all_elements(base_object) -> list:
    """
    Cerca ricorsivamente in un oggetto Speckle tutti gli elementi,
    indipendentemente da quanto sono annidati in liste o collezioni.
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
    Esegue la Regola #1: Verifica che tutti i muri e solai abbiano
    il parametro 'FireRating' compilato.
    """
    print("--- AVVIO REGOLA #1: CENSIMENTO ANTINCENDIO ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("Nessun elemento Revit trovato nel commit.")
            return

        print(f"Trovati {len(all_elements)} elementi totali da analizzare.", flush=True)

        validation_errors = []
        objects_validated = 0
        for el in all_elements:
            category = getattr(el, 'category', '')
            
            if any(target.lower() in category.lower() for target in TARGET_CATEGORIES):
                objects_validated += 1
                print(f"-> Elemento {el.id} (Categoria: {category}) identificato come target. Procedo con la validazione.", flush=True)
                
                # --- SOLUZIONE DEFINITIVA APPLICATA QUI ---
                # 1. Accediamo all'oggetto 'properties' usando getattr, perché 'el' è un oggetto Speckle.
                properties = getattr(el, 'properties', None)
                if not properties:
                    print(f"ERRORE: L'elemento {el.id} non ha 'properties'.", flush=True)
                    validation_errors.append(el.id)
                    continue

                # 2. All'interno di 'properties' (che è un dizionario), cerchiamo 'Parameters'.
                revit_parameters = properties.get('Parameters', {})
                if not revit_parameters:
                    print(f"ERRORE: L'elemento {el.id} non ha un oggetto 'Parameters' dentro 'properties'.", flush=True)
                    validation_errors.append(el.id)
                    continue

                # 3. All'interno di 'Parameters', cerchiamo 'Instance Parameters'.
                instance_params = revit_parameters.get('Instance Parameters', {})
                if not instance_params:
                    print(f"ERRORE: L'elemento {el.id} non ha 'Instance Parameters'.", flush=True)
                    validation_errors.append(el.id)
                    continue

                # 4. Cerchiamo il nostro parametro dentro 'Instance Parameters'.
                fire_rating_param = instance_params.get(FIRE_RATING_PARAM)
                
                if not fire_rating_param or getattr(fire_rating_param, 'value', None) is None:
                    print(f"ERRORE: L'elemento {el.id} non ha un '{FIRE_RATING_PARAM}' valido.", flush=True)
                    validation_errors.append(el.id)

        print(f"Validazione completata. {objects_validated} oggetti sono stati controllati.", flush=True)

        if validation_errors:
            error_message = f"Validazione fallita: {len(validation_errors)} elementi non hanno il parametro '{FIRE_RATING_PARAM}' compilato."
            
            ctx.attach_error_to_objects(
                category=f"Dati Mancanti: {FIRE_RATING_PARAM}",
                object_ids=validation_errors,
                message=f"Il parametro '{FIRE_RATING_PARAM}' e mancante o
