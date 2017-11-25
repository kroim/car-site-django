from django import template
from django.contrib.auth.models import Group
register = template.Library()

@register.filter(name='is_limited_employee')
def is_limited_employee(user):
    if user and user.is_superuser:
        return False

    group = Group.objects.get(name='employee2')
    return group in user.groups.all()

