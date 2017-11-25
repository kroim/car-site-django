# -*- coding: UTF-8 -*-
from __future__ import division

from django.core.management.base import BaseCommand

from crawler.models import *

class Command(BaseCommand):
    help = 'update colors based on existing cars'

    def handle(self, *args, **options):
        cars = Car.objects.all()
        colors = Color.objects.all()

        colors_hashmap = {}
        for color in colors:
            colors_hashmap[color.name.lower()] = True

        temp = {}

        for car in cars:
            exterior = car.cardetail.exterior
            if exterior != None and len(exterior) > 0 and not exterior.lower() in colors_hashmap:
                if exterior.lower() in temp:
                    # Just Colors that are repeated more than 5 times in whole car history
                    if temp[exterior.lower()] > 5:

                        colors_hashmap[exterior.lower()] = True

                        # add color to Colors
                        new_color = Color(name=exterior.lower())
                        new_color.save()

                        print exterior.lower()
                    else:
                        temp[exterior.lower()] += 1
                else:
                    temp[exterior.lower()] = 1