# main.py
# SCRIPT DI DIAGNOSI DEFINITIVA
# Questo script non prova a risolvere il problema, ma ci darà la chiave per risolverlo.

from speckle_automate import AutomationContext, execute_automate_function

def main(ctx: AutomationContext) -> None:
    """
    Questa funzione ha un solo scopo: ispezionare l'oggetto AutomationContext (ctx)
    e stampare una lista di tutti i suoi metodi e attributi disponibili.
    Questo ci dirà il nome corretto della funzione da usare per ottenere i dati.
    """
    print("--- AVVIO SCRIPT DI DIAGNOSI DEFINITIVA ---", flush=True)
    
    try:
        print("\n--- Ispezione dell'oggetto 'AutomationContext' (ctx) ---", flush=True)
        
        # Usiamo la funzione dir() di Python per ottenere una lista di tutto
        # ciò che è disponibile all'interno dell'oggetto ctx.
        available_attributes = dir(ctx)
        
        print("Attributi e metodi disponibili in 'ctx':", flush=True)
        for attr in available_attributes:
            # Stampiamo ogni attributo/metodo disponibile.
            # Cercheremo in questa lista un nome che assomigli a "get_..._data" o "get_..._object".
            print(f"  - {attr}", flush=True)
            
        print("\n--- Ispezione completata ---", flush=True)

        ctx.mark_run_succeeded("Diagnosi completata. Controllare i log per la lista dei metodi.")

    except Exception as e:
        error_message = f"Errore durante la diagnosi: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- FINE SCRIPT DI DIAGNOSI ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
