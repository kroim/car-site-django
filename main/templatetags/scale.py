from django import template
register = template.Library()

@register.filter(name='grade_scale')
def grade_scale(value):
    if value == None:
        return None

    return round((value / 5.0) * 0.6 + 9.0, 1)