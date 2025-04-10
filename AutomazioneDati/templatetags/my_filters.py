from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Data una chiave, ritorna il valore corrispondente all'interno del dizionario."""
    return dictionary.get(key)

@register.filter(name='format_decimal')
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