from django import template
import calendar # Importa il modulo calendar di Python

register = template.Library()

@register.filter
def get_item(sequence, key):
    """Returns the item at the given key/index from a sequence (list, dict)."""
    try:
        # Prova prima come dizionario
        return sequence[key]
    except (KeyError, TypeError):
        try:
            # Prova come lista/tupla (assicurati che key sia un intero)
            return sequence[int(key)]
        except (IndexError, ValueError, TypeError):
             # Se key non è un intero valido o l'indice è fuori range, o non è né dict né sequence
            return None # Restituisce None se la chiave/indice non è valido o l'oggetto non è indicizzabile

@register.filter
def format_decimal(value, decimal_places=3):
    """Formatta un valore decimal con la virgola come separatore decimale."""
    if value is None:
        return ""
    try:
        # Formatta con un numero fisso di decimali e sostituisce il punto con la virgola
        formatted_value = f"{value:.{decimal_places}f}".replace('.', ',')
        return formatted_value
    except (ValueError, TypeError):
        return str(value)  # Restituisce il valore originale se la formattazione fallisce

@register.filter
def get_attr(obj, attr):
    """Restituisce l'attributo di un oggetto dato il nome dell'attributo."""
    # Versione semplice: restituisce l'attributo o None se non esiste.
    # La logica complessa per data_presa è stata rimossa da custom_filters.py
    try:
        return getattr(obj, attr)
    except (AttributeError, TypeError):
        return None

@register.filter(name='month_name')
def month_name(month_number):
    """Converte un numero di mese (1-12) nel nome del mese in italiano."""
    # Dizionario con i nomi dei mesi in italiano
    mesi = {
        1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
        5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
        9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
    }
    try:
        # Converte il numero in intero e restituisce il nome dal dizionario
        return mesi.get(int(month_number))
    except (ValueError, TypeError):
        # Se il valore non è un numero o non è nel range 1-12, restituisce una stringa vuota o il valore originale
        return "" # O potresti restituire month_number per vedere cosa è andato storto 