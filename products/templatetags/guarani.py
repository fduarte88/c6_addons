from django import template

register = template.Library()


@register.filter
def gs(value):
    """
    Formatea un número como moneda Guaraní paraguaya.
    Sin decimales, con punto como separador de miles.
    Ejemplo: 1500000 → Gs. 1.500.000
    """
    try:
        amount = int(round(float(value)))
        # Formato con coma como miles, luego reemplazamos por punto
        formatted = f'{amount:,}'.replace(',', '.')
        return f'Gs. {formatted}'
    except (ValueError, TypeError):
        return 'Gs. 0'


@register.filter
def gs_plain(value):
    """
    Solo el número formateado sin el prefijo Gs.
    Útil para inputs y campos donde el símbolo va aparte.
    Ejemplo: 1500000 → 1.500.000
    """
    try:
        amount = int(round(float(value)))
        return f'{amount:,}'.replace(',', '.')
    except (ValueError, TypeError):
        return '0'
