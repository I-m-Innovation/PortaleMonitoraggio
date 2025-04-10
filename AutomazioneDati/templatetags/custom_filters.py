from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Restituisce il valore di un dizionario per una chiave data"""
    return dictionary.get(key)

@register.filter
def get_attr(obj, attr):
    """Restituisce l'attributo di un oggetto dato il nome dell'attributo"""
    if hasattr(obj, attr):
        return getattr(obj, attr)
    elif attr == 'data_presa_display' and hasattr(obj, 'data_presa'):
        # Formatta la data se l'attributo 'data_presa_display' non esiste ma 'data_presa' sì
        data_presa = getattr(obj, 'data_presa')
        if data_presa:
            # Converti in formato GG/MM/AAAA
            try:
                if '-' in str(data_presa):
                    parts = str(data_presa).split('-')
                    if len(parts) == 3:
                        year, month, day = parts
                        return f"{day}/{month}/{year}"
            except Exception:
                pass
        return str(data_presa) if data_presa else ""
    return "" 