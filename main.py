# main.py
# Script di ispezione finale per scoprire il 'speckle_type' esatto degli elementi.
# AGGIORNAMENTO: Aggiunta la logica per ispezionare dentro gli 'Objects.Data.DataObject'.

from speckle_automate import AutomationContext, execute_automate_function

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
    Esegue un'ispezione finale per stampare il 'speckle_type' di ogni elemento trovato.
    """
    print("--- AVVIO ISPEZIONE FINALE DEI TIPI ---", flush=True)
    
    try:
        commit_root_object = ctx.receive_version()
        all_elements = find_all_elements(commit_root_object)

        if not all_elements:
            ctx.mark_run_success("Nessun elemento Revit trovato nel commit.")
            return

        print(f"Trovati {len(all_elements)} elementi. Ispezione dei loro 'speckle_type':", flush=True)

        # Iteriamo su ogni elemento e stampiamo il suo tipo.
        for i, el in enumerate(all_elements):
            speckle_type = getattr(el, 'speckle_type', 'TIPO NON TROVATO')
            print(f"  - Elemento Contenitore #{i+1}: {speckle_type}", flush=True)

            # --- NUOVA LOGICA DI ISPEZIONE ---
            # Se l'elemento è un DataObject, proviamo a guardare dentro.
            if speckle_type == "Objects.Data.DataObject":
                print("    -> È un DataObject, ispeziono il suo contenuto:", flush=True)
                # I dati reali sono spesso in una proprietà dinamica.
                # Iteriamo su tutte le proprietà per trovarli.
                for prop_name in el.get_member_names():
                    inner_value = getattr(el, prop_name)
                    if isinstance(inner_value, list):
                        for inner_item in inner_value:
                            if hasattr(inner_item, "speckle_type"):
                                print(f"      - Oggetto Interno: {getattr(inner_item, 'speckle_type', 'N/A')}", flush=True)
                    elif hasattr(inner_value, "speckle_type"):
                         print(f"      - Oggetto Interno: {getattr(inner_value, 'speckle_type', 'N/A')}", flush=True)


        ctx.mark_run_success("Ispezione dei tipi completata. Controllare i log.")

    except Exception as e:
        error_message = f"Errore durante l'esecuzione dello script: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- FINE ISPEZIONE FINALE ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
