# main.py
# Versione corretta con il metodo aggiornato per ottenere i dati del commit.
# AGGIORNAMENTO FINALE: Usiamo 'get_version_root_object' come da documentazione ufficiale.

from speckle_automate import AutomationContext, execute_automate_function

def main(ctx: AutomationContext) -> None:
    """
    Questa funzione ha un solo scopo: ricevere il commit e stampare la sua
    struttura completa per capire come sono organizzati i dati.
    """
    print("--- AVVIO SCRIPT DI ISPEZIONE DATI (v. corretta) ---", flush=True)
    
    try:
        # --- CORREZIONE DEFINITIVA APPLICATA QUI ---
        # Il metodo corretto e attuale per ottenere i dati è 'get_version_root_object'.
        version_root_object = ctx.get_version_root_object()
        
        print(f"Oggetto radice ricevuto. Tipo: {getattr(version_root_object, 'speckle_type', 'N/A')}", flush=True)

        # I dati da Revit sono spesso in una lista chiamata 'elements' o '@elements'.
        elements = getattr(version_root_object, 'elements', None)
        if not elements:
             elements = getattr(version_root_object, '@elements', None) # Prova anche con la @
        
        if not elements:
            print("ERRORE: Non è stata trovata una lista 'elements' o '@elements' nell'oggetto radice.", flush=True)
            ctx.mark_run_failed("La struttura del commit non è quella attesa.")
            return

        print(f"Trovati {len(elements)} elementi nella lista.", flush=True)

        if not elements:
            ctx.mark_run_succeeded("Il commit è vuoto.")
            return

        # Prendiamo il primo elemento della lista e lo ispezioniamo.
        first_element = elements[0]
        print("\n--- ISPEZIONE DEL PRIMO ELEMENTO TROVATO ---", flush=True)
        print(f"ID Oggetto: {getattr(first_element, 'id', 'N/A')}", flush=True)
        print(f"Speckle Type: {getattr(first_element, 'speckle_type', 'N/A')}", flush=True)
        
        print("\n--- PROPRIETÀ DI PRIMO LIVELLO ---", flush=True)
        for prop_name in first_element.get_member_names():
            print(f"  - {prop_name}", flush=True)

        # Cerchiamo i parametri, che in Revit sono spesso annidati.
        parameters = getattr(first_element, 'parameters', None)
        if parameters:
            print("\n--- ISPEZIONE DEI PARAMETRI NESTATI ---", flush=True)
            
            if hasattr(parameters, 'get_member_names'):
                for param_name in parameters.get_member_names():
                    try:
                        param_value = getattr(parameters, param_name)
                        if hasattr(param_value, 'value'):
                             print(f"  - {getattr(param_value, 'name', param_name)}: {getattr(param_value, 'value', 'N/A')}", flush=True)
                    except:
                        continue
        else:
            print("\nNessun oggetto 'parameters' trovato nel primo elemento.", flush=True)

        ctx.mark_run_succeeded("Ispezione dati completata. Controllare i log.")

    except Exception as e:
        error_message = f"Errore durante l'ispezione dei dati: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- FINE SCRIPT DI ISPEZIONE DATI ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
