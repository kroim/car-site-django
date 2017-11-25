# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.core.management import call_command

@shared_task
def apply_damage_rule(damage_rule_id):
    call_command('calculate_final_prices', 'current_unresolved_cars', damagerule=damage_rule_id)

@shared_task
def calculate_mo_prices():
    call_command('calculate_final_prices', 'mo_cars')

@shared_task
def calculate_bg_prices():
    call_command('calculate_final_prices', 'bg_cars')

@shared_task
def calculate_ove_prices():
    call_command('calculate_final_prices', 'ove_cars')

@shared_task
def calculate_ade_prices():
    call_command('calculate_final_prices', 'ade_cars')

@shared_task
def mo_all():
    call_command('mo', 'all')

@shared_task
def bg_all():
    call_command('bg', 'all')

@shared_task
def ove_all():
    call_command('ove', 'all')

@shared_task
def ade_all():
    call_command('ade', 'all', '-withremove')