# main.py
# SCRIPT DI DIAGNOSI DEFINITIVA per l'errore 'ids' vs 'object_ids'

import inspect
from speckle_automate import AutomationContext, execute_automate_function

def main(ctx: AutomationContext) -> None:
    """
    Questa funzione ha un solo scopo: ispezionare la funzione 'attach_error_to_objects'
    e stampare i nomi esatti dei suoi parametri. Questo risolverà il dubbio
    'ids' vs 'object_ids' una volta per tutte.
    """
    print("--- AVVIO DIAGNOSI DEFINITIVA: attach_error_to_objects ---", flush=True)
    
    try:
        # Usiamo il modulo 'inspect' di Python per ottenere la firma della funzione
        signature = inspect.signature(ctx.attach_error_to_objects)
        parameters = signature.parameters
        
        print("\n--- Analisi della funzione 'attach_error_to_objects' ---", flush=True)
        print("Parametri richiesti dalla funzione:", flush=True)
        
        param_names = list(parameters.keys())
        for name in param_names:
            print(f"  - {name}", flush=True)
            
        print("\n--- Diagnosi completata ---", flush=True)

        # Eseguiamo un test fittizio per confermare che la funzione esista,
        # ma senza usare l'argomento problematico per evitare errori.
        ctx.mark_run_success("Diagnosi completata. Controllare i log per i nomi dei parametri.")

    except Exception as e:
        error_message = f"Errore durante la diagnosi: {e}"
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- FINE DIAGNOSI DEFINITIVA ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
