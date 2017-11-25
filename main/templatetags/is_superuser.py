from django import template

register = template.Library()

@register.filter(name='is_superuser')
def is_superuser(user):
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    for group in user.groups.all():
        if group.name == 'employee1' or group.name == 'employee2':
            return True
    return False