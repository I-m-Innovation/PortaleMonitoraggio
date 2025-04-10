from django import template

register = template.Library()

@register.filter
def get_item(sequence, key):
    """Returns the item at the given key/index from a sequence (list, dict)."""
    try:
        return sequence[key]
    except (KeyError, IndexError, TypeError):
        return None # Restituisce None se l'indice non è valido o l'oggetto non è indicizzabile

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
    try:
        return getattr(obj, attr)
    except (AttributeError, TypeError):
        return None 