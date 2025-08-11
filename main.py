# main.py
# VERSIONE 14.0 - RICOGNITORE (ASCOLTA E RIPORTA LE DESCRIZIONI)

import json
import traceback
from speckle_automate import AutomationContext, execute_automate_function

#============== CONFIGURAZIONE (Solo per la lettura dei parametri) =================
GRUPPO_DATI_IDENTITA = "Dati identità"
COST_DESC_PARAM_NAME = "Descrizione"
#=====================================================================================

#============== FUNZIONI HELPER ======================================================
def find_all_elements(base_object) -> list:
    elements = []
    element_container = getattr(base_object, '@elements', None) or getattr(base_object, 'elements', None)
    if element_container and isinstance(element_container, list):
        for element in element_container: elements.extend(find_all_elements(element))
    elif isinstance(base_object, list):
        for item in base_object: elements.extend(find_all_elements(item))
    if getattr(base_object, 'id', None) is not None and "Objects.Organization.Model" not in getattr(base_object, 'speckle_type', ''):
        elements.append(base_object)
    return elements

def get_type_parameter_value(element, group_name: str, param_name: str):
    try: return element.properties['Parameters']['Type Parameters'][group_name][param_name]['value']
    except (AttributeError, KeyError, TypeError): return None

#============== ORCHESTRATORE DI RICOGNIZIONE =======================================
def main(ctx: AutomationContext) -> None:
    print("--- STARTING RECONNAISSANCE SCRIPT (v14.0) ---", flush=True)
    try:
        all_elements = find_all_elements(ctx.receive_version())
        if not all_elements:
            ctx.mark_run_success("Nessun elemento processabile trovato.")
            return

        print(f"Trovati {len(all_elements)} elementi. Inizio scansione delle descrizioni...")
        
        unique_descriptions = set()

        for el in all_elements:
            description = get_type_parameter_value(el, GRUPPO_DATI_IDENTITA, COST_DESC_PARAM_NAME)
            category = getattr(el, 'category', 'N/A')
            
            if description: # Se abbiamo trovato una descrizione
                # Aggiungiamo una tupla al set per evitare duplicati
                unique_descriptions.add((category, description))

        if unique_descriptions:
            print("\n\n" + "="*40)
            print("--- DESCRIZIONI UNICHE TROVATE NEL MODELLO ---")
            for category, description in sorted(list(unique_descriptions)):
                print(f"- Categoria '{category}': '{description}'")
            print("============================================\n\n")
            ctx.mark_run_success("Scansione completata. Copia le descrizioni dal log nel tuo prezzario.json.")
        else:
            ctx.mark_run_failed("Nessuna descrizione trovata. Assicurati che il parametro di Tipo 'Descrizione' nel gruppo 'Dati identità' sia compilato per almeno un elemento.")

    except Exception as e:
        error_message = f"Errore critico durante la scansione: {e}"
        traceback.print_exc()
        print(error_message, flush=True)
        ctx.mark_run_failed(error_message)

    print("--- RECONNAISSANCE SCRIPT FINISHED ---", flush=True)

if __name__ == "__main__":
    execute_automate_function(main)
