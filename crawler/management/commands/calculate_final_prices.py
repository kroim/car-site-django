# -*- coding: UTF-8 -*-
from __future__ import division
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

import re, operator

from crawler.models import *

counter = 0


def car_qulification(car, damage_rules, recalculate):
    global counter

    if recalculate == True:
        car.is_rejected = False
        car.rejection_reason = None
        car.eligible_to_display = False
        car.final_price = None
    else:
        if car.is_rejected == True or car.eligible_to_display == True:
            return

    # No Price Rejection
    if car.original_price == None:
        car.is_rejected = True
        car.rejection_reason = "NO PRICE was found on original website!"
        car.save()
        return

    # Mile Rejection
    if car.cardetail.miles >= 49800:  # TODO: put 49800 as setting in database
        car.is_rejected = True
        car.rejection_reason = "Car Mileage is more than 49800"
        car.save()
        return

    # Odor Rejection
    # car_odor = car.cardetail.odor
    # if car_odor != None and (car_odor.lower().strip() == 'smoke' or car_odor.lower().strip() == 'foul'):
    #     car.is_rejected = True
    #     car.rejection_reason = "Odor"
    #     car.save()
    #     return

    # Unibody/Frame/Structural Damage Rejection
    car_announcements = car.cardetail.announcements
    if car_announcements != None and ('unibody damage' in car_announcements.lower() or 'structural damage' in car_announcements.lower() or 'structural repair' in car_announcements.lower()):
        car.is_rejected = True
        car.rejection_reason = "Because of unibody damage or structural damage or structural repair in announcements."
        car.save()
        return

    price = car.original_price

    # Add Shipping Cost
    if car.location != None:
        price += car.location.shipping_cost
    else:
        # Don't know shipping cost
        print "Unknown Location --> car: ", car.id
        car.is_rejected = True
        car.rejection_reason = "Unknown Location"
        car.save()
        return

    without_price_damages = []
    has_without_price_damage = False
    has_rejection_damage = False

    # TODO: Put these prices in database
    if car.ade_car_id != None:
        if car.original_price < 20000:
            price += 1900
            price += 250  # Auction Fee
        elif car.original_price >= 20000 and car.original_price < 37000:
            price += 2300
            price += 350  # Auction Fee
        else:
            price += 3700
            price += 350  # Auction Fee

        price += 120  # detail, smoke, odor
    elif car.mo_car_id != None:
        if car.original_price < 20000:
            price += 1900
        elif car.original_price >= 20000 and car.original_price < 37000:
            price += 2300
        else:
            price += 3700

        price += 250  # Auction Fee
        price += 220  # detail, smoke, odor
    elif car.ove_car_id != None:
        if car.original_price < 20000:
            price += 1900
        elif car.original_price >= 20000 and car.original_price < 37000:
            price += 2300
        else:
            price += 3700

        price += 325  # Auction Fee
        price += 220  # detail, smoke, odor
    elif car.bg_car_id != None:
        if car.original_price < 20000:
            price += 1900
        elif car.original_price >= 20000 and car.original_price < 37000:
            price += 2300
        else:
            price += 3700

        price += 250  # Auction Fee
        price += 220  # detail, smoke, odor

    damage_rules_regexes = []

    for damage_rule in damage_rules:
        # if damage_rule.id != 1:
        #     continue

        damage_rules_regexes.append({
            'part': re.compile(damage_rule.part) if damage_rule.part != '.*' else True,
            'condition': re.compile(damage_rule.condition) if damage_rule.condition != '.*' else True,
            'severity': re.compile(damage_rule.severity) if damage_rule.severity != '.*' else True,
            'car_model': re.compile(damage_rule.car_model) if damage_rule.car_model != '.*' else True,
            'price': damage_rule.price,
            'id': damage_rule.id,
        })

    inch_pattern = re.compile('(\d+(\.\d+)?)"([<|>][=]?)')
    number_pattern = re.compile('(\d+(\.\d+)?)([<|>][=]?)')

    scratch_heavy_counter = 0
    scratch_light_counter = 0

    total_damage_price = 0
    ff = False
    gg = False

    for damage in car.damage_set.all():

        # damage = Damage.objects.get(id=21950)

        if recalculate == False and damage.estimated_price != None:
            total_damage_price += damage.estimated_price
            continue

        if damage.estimated_price != None and damage.mannual == True:
            # It was filled before mannually
            total_damage_price += damage.estimated_price
            continue

        part = ' '.join(damage.part.lower().strip().split())
        condition = ' '.join(damage.condition.lower().strip().split())
        severity = ' '.join(damage.severity.lower().strip().split())

        damage_dict = {}
        damage_dict['part'] = part
        damage_dict['condition'] = condition
        damage_dict['severity'] = severity
        damage_dict['car_model'] = car.model.name if car.model != None else '*'

        severity_value, severity_type = parse_severity(severity)

        if 'scratch heavy' in condition:
            scratch_heavy_counter += 1
        if 'scratch light' in condition:
            scratch_light_counter += 1

        estimated_damage_price = None
        effective_damage_rule_id = None

        for damage_rules_regex in damage_rules_regexes:
            keys = ['part', 'condition', 'severity', 'car_model']
            matched = True
            for key in keys:
                if damage_rules_regex[key] == True:
                    continue
                result = damage_rules_regex[key].match(damage_dict[key])

                if result != None and result.span() == (0, len(damage_dict[key])):
                    continue

                if key == 'severity':
                    # 1<= 1< 1> 1>= 1"<= 1"< 1"> 1">= ...

                    # Inch Pattern
                    result = inch_pattern.match(damage_rules_regex[key].pattern)
                    if result != None and result.span() == (0, len(damage_rules_regex[key].pattern)):
                        num = float(result.group(1))
                        operation = result.group(3)
                        if severity_value != None and severity_type == 'inch_range':
                            if operation == '<' and num < severity_value[1]:
                                continue
                            if operation == '<=' and num <= severity_value[1]:
                                continue
                            if operation == '>' and num > severity_value[0]:
                                continue
                            if operation == '>=' and num >= severity_value[0]:
                                continue

                    # Number Pattern
                    result = number_pattern.match(damage_rules_regex[key].pattern)
                    if result != None and result.span() == (0, len(damage_rules_regex[key].pattern)):
                        num = float(result.group(1))
                        operation = result.group(3)
                        if severity_value != None and severity_type == 'number_range':
                            if operation == '<' and num < severity_value[1]:
                                continue
                            if operation == '<=' and num <= severity_value[1]:
                                continue
                            if operation == '>' and num > severity_value[0]:
                                continue
                            if operation == '>=' and num >= severity_value[0]:
                                continue

                        if severity_value != None and severity_type == 'number':
                            if operation == '<' and num < severity_value:
                                continue
                            if operation == '<=' and num <= severity_value:
                                continue
                            if operation == '>' and num > severity_value:
                                continue
                            if operation == '>=' and num >= severity_value:
                                continue

                matched = False
                break

            if matched == True:
                if damage_rules_regex['price'] == -1:
                    has_rejection_damage = True

                effective_damage_rule_id = damage_rules_regex['id']
                estimated_damage_price = damage_rules_regex['price']
                break

        if estimated_damage_price != None:
            damage.estimated_price = estimated_damage_price
            damage.effective_damage_rule = DamageRule.objects.get(id=effective_damage_rule_id)
            damage.mannual = False
            damage.save()
            total_damage_price += estimated_damage_price
        else:

            # TEMP 2016 and 2017
            if (car.year == 2017 or car.year == 2016) and car.make.name != "Mercedes Benz" and car.make.name != "BMW":
                if ff == False:
                    damage.estimated_price = 300
                    ff = True
                else:
                    damage.estimated_price = 0
                damage.mannual = False
                damage.save()
                # TEMP 2016 and 2017
            elif (car.year == 2014 or car.year == 2015) and car.make.name != "Mercedes Benz" and car.make.name != "BMW":
                if gg == False:
                    damage.estimated_price = 400
                    gg = True
                else:
                    damage.estimated_price = 0
                damage.mannual = False
                damage.save()
            else:
                damage.estimated_price = None
                damage.mannual = None
                damage.save()

                without_price_damages.append(damage)

                has_without_price_damage = True
                counter += 1

    # if scratch_heavy_counter >= 4:
    #     has_rejection_damage = True
    # if scratch_light_counter >= 8:
    #     has_rejection_damage = True

    # if total_damage_price >= 1750:
    #     has_rejection_damage = True

    # TEMP
    if len(without_price_damages) == 1:
        has_without_price_damage = False
        damage = without_price_damages[0]
        damage.estimated_price = 200
        damage.mannual = False
        damage.save()

    if has_rejection_damage == True:
        car.is_rejected = True
        car.rejection_reason = "Has one or more damages that cause rejection"
        car.eligible_to_display = False
        car.save()
    elif has_without_price_damage == False:
        price += total_damage_price
        car.final_price = price
        car.is_rejected = False
        car.eligible_to_display = True
        car.save()
    else:
        car.is_rejected = False
        car.eligible_to_display = False
        car.save()


def parse_severity(severity):
    inch_range_patterns = ['([0-9]+/)?[0-9]+\" to ([0-9]+/)?[0-9]+\"',
                           '(?i)gr [0-9]+\"',
                           '(?i)[0-9]+ - [0-9]+ inch(es)?',
                           '(?i)([0-9]+)[+] inches',
                           '(<|>) ([0-9]+/)?[0-9]+\"',
                           '(?i)less than [0-9]+ inch(es)?']

    for i in range(len(inch_range_patterns)):
        pattern = inch_range_patterns[i]
        prog = re.compile(pattern)
        matching = prog.match(severity)
        ans_range = None
        if matching != None and matching.span()[0] == 0 and matching.span()[1] == len(severity):
            if i == 0:
                t = re.search('(.*)\" to (.*)\"', severity, re.IGNORECASE)
                ans_range = (eval(t.group(1)), eval(t.group(2)))
            elif i == 1:
                t = re.search('(?i)gr (.*)\"', severity, re.IGNORECASE)
                ans_range = (eval(t.group(1)), float('inf'))
            elif i == 2:
                t = re.search('(?i)(.*) - (.*) inch(es)?', severity, re.IGNORECASE)
                ans_range = (eval(t.group(1)), eval(t.group(2)))
            elif i == 3:
                t = re.search('(?i)(.*)[+] inches', severity, re.IGNORECASE)
                ans_range = (eval(t.group(1)), float('+inf'))
            elif i == 4:
                t = re.search('(<|>) (.*)\"', severity, re.IGNORECASE)
                if t.group(1) == '<':
                    ans_range = (float('-inf'), eval(t.group(2)))
                elif t.group(1) == '>':
                    ans_range = (eval(t.group(2)), float('inf'))
            elif i == 5:
                t = re.search('(?i)less than (.*) inch(es)?', severity, re.IGNORECASE)
                ans_range = (float('-inf'), eval(t.group(1)))

            # print '=========='
            # print severity
            # print ans_range
            # print '=========='

            return ans_range, 'inch_range'

    number_patterns = ['[0-9]+']

    for i in range(len(number_patterns)):
        pattern = number_patterns[i]
        prog = re.compile(pattern)
        matching = prog.match(severity)
        if matching != None and matching.span()[0] == 0 and matching.span()[1] == len(severity):
            if i == 0:
                t = re.search('(.*)', severity, re.IGNORECASE)
                ans = int(t.group(1))

            return ans, 'number'

    number_range_patterns = ['(?i)[0-9]+ or more']

    for i in range(len(number_range_patterns)):
        pattern = number_range_patterns[i]
        prog = re.compile(pattern)
        matching = prog.match(severity)
        ans_range = None
        if matching != None and matching.span()[0] == 0 and matching.span()[1] == len(severity):
            if i == 0:
                t = re.search('(?i)(.*) or more', severity, re.IGNORECASE)
                ans_range = (eval(t.group(1)), float('inf'))

            return ans_range, 'number_range'

    return None, None


class Command(BaseCommand):
    help = 'Calculate final prices of current vehicles'

    def add_arguments(self, parser):
        parser.add_argument('type', type=str)

        # Named (optional) argument
        parser.add_argument(
            '-damagerule',
            action='store',
            dest='damagerule',
            default=False,
            help='Specific Damage Rule id',
        )

        # Named (optional) argument
        parser.add_argument(
            '-car',
            action='store',
            dest='car',
            default=False,
            help='Specific Car id',
        )

    def handle(self, *args, **options):
        global counter
        counter = 0

        recalculate = True

        if options['type'] == 'current_cars':
            cars = Car.objects.filter(is_it_available=True).order_by('-id')
        if options['type'] == 'mo_cars':
            cars = Car.objects.filter(is_it_available=True, available_on_mo=True, mo_car_id__isnull=False).order_by('-id')
        if options['type'] == 'bg_cars':
            cars = Car.objects.filter(is_it_available=True, available_on_bg=True, bg_car_id__isnull=False).order_by('-id')
        if options['type'] == 'ove_cars':
            cars = Car.objects.filter(is_it_available=True, available_on_ove=True, ove_car_id__isnull=False).order_by('-id')
        if options['type'] == 'ade_cars':
            cars = Car.objects.filter(is_it_available=True, available_on_ade=True, ade_car_id__isnull=False).order_by('-id')
        if options['type'] == 'current_unresolved_cars':
            cars = Car.objects.filter(is_it_available=True, is_rejected=False, eligible_to_display=False).order_by('-id')
            recalculate = False
        elif options['type'] == 'all_cars':
            cars = Car.objects.all().order_by('-id')
        elif options['type'] == 'single':
            # options['car'] Should not be False
            cars = Car.objects.filter(id=options['car'])
            recalculate = False


        if options['damagerule'] != False:
            damage_rules = DamageRule.objects.filter(
                reduce(operator.or_, (Q(id=x) for x in [options['damagerule']]))) # array of ids --> now 1 id
        else:
            damage_rules = DamageRule.objects.all()  # Load all damage rules

        c = 1
        for car in cars:
            car_qulification(car, damage_rules, recalculate)
            print c
            c += 1
        print '-------->', counter
