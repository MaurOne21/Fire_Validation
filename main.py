# main.py
# Versione funzionante della Regola #1: Censimento Antincendio.
# Utilizza i nomi delle categorie in italiano scoperti tramite il debug.

from speckle_automate import AutomationContext, execute_automate_function

# Definiamo le CATEGORIE di Revit che vogliamo controllare.
# Usiamo i nomi esatti che abbiamo scoperto: "Muri" e "Pavimenti".
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
    il parametro 'FireRating' compila
