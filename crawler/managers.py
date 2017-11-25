from django.db import models
from django.db.models import Q
from django.utils import timezone


class CarManager(models.Manager):
    def available_eligible_cars(self):
        return self.filter(
            (Q(is_it_available=True) | (Q(remain_until__isnull=False) & Q(remain_until__gt=timezone.now())) | Q(remain_permatently=True)) & (
            Q(is_rejected=False) & Q(eligible_to_display=True) & Q(make__is_visible=True) & Q(
                removed_permanently=False)))

    def available_cars(self):
        return self.filter(
            (Q(is_it_available=True) | (Q(remain_until__isnull=False) & Q(remain_until__gt=timezone.now())) | Q(remain_permatently=True)) & Q(
                make__is_visible=True))
