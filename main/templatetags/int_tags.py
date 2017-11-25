from django import template
register = template.Library()

@register.filter(name='thousands_separator')
def thousands_separator(value):
    if value == None:
        return None
    return '{:,}'.format(value)

@register.filter(name='human_format')
def human_format(value):
    if value == None:
        return None
    magnitude = 0
    while abs(value) >= 1000:
        magnitude += 1
        value /= 1000

    ans = '%d%s' % (value, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])
    return ans