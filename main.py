# main.py
# Test di "Hello World" per verificare la cattura dei log.

from speckle_automate import AutomationContext

def main(ctx: AutomationContext) -> None:
    """
    Questa funzione esegue il test più semplice possibile: stampa un messaggio
    e termina con successo. Serve a verificare se i log vengono visualizzati.
    """
    print("--- TEST SEMPLIFICATO INIZIATO ---", flush=True)
    print("Se vedi questo messaggio, il metodo requirements.txt funziona.", flush=True)

    ctx.mark_run_succeeded("Test di logging con requirements.txt completato.")

    print("--- TEST SEMPLIFICATO TERMINATO ---", flush=True)
