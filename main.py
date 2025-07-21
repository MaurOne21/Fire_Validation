# main.py
# Test di "Hello World" per verificare la cattura dei log.

from speckle_automate import AutomationContext

def main(ctx: AutomationContext) -> None:
    """
    Questa funzione esegue il test più semplice possibile: stampa un messaggio
    e termina con successo. Serve a verificare se i log vengono visualizzati.
    """
    print("--- TEST DI LOGGING INIZIATO ---", flush=True)
    print("Se vedi questo messaggio, la cattura dei log funziona.", flush=True)
    print("Questo è il test definitivo.", flush=True)
    
    # Non interagiamo con i dati di Speckle, terminiamo e basta.
    # Questo ci permette di isolare il problema.
    ctx.mark_run_succeeded("Test di logging completato con successo.")
    
    print("--- TEST DI LOGGING TERMINATO ---", flush=True)
