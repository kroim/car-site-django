from django import template
register = template.Library()

@register.filter(name='normalize_price')
def normalize_price(value):
    if value == None:
        return None

    if value % 1000 < 70:
        return (value/1000)*1000-50
    if value % 100 > 0 and value % 100 < 50:
        return value - value%100 + 50
    if value % 100 > 50:
        return value - value%100 + 100
    return value