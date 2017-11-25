from django.shortcuts import render, redirect

from django.http import HttpResponse
from django.core.management import call_command
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate
from django.contrib import messages

from crawler.models import *

import django, re, os

from administrator.tasks import apply_damage_rule, calculate_mo_prices, calculate_bg_prices, \
    calculate_ove_prices, calculate_ade_prices, mo_all, bg_all, ove_all, ade_all


def login(request):
    if (request.user.is_authenticated()):
        return HttpResponse('Access Denied')
        # if 'next' in request.GET:
        #     return redirect(request.GET['next'])
        # return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user != None:
            django.contrib.auth.login(request, user)
            if 'next' in request.GET:
                return redirect(request.GET['next'])
            return redirect('dashboard')
        else:
            messages.add_message(request, messages.ERROR, 'Wrong username or password')

    context = {}
    return render(request, 'administrator/login.html', context)


def signout(request):
    django.contrib.auth.logout(request)
    next = 'login'
    if ('next' in request.GET):
        next = request.GET['next']

    return redirect(next)


@user_passes_test(lambda u: u.is_superuser or u.groups.filter(Q(name='employee1') | Q(name='employee2')).count() > 0)
def dashboard(request):
    cars_count = Car.objects.available_eligible_cars().count()
    damage_count = Damage.objects.filter(car__is_it_available=True, car__is_rejected=False,
                                         car__eligible_to_display=False, estimated_price__isnull=True,
                                         car__make__is_visible=True).count()
    contacts_count = Contact.objects.all().count()
    crawlers = Crawler.objects.all().order_by('name')

    context = {'cars_count': cars_count, 'damage_count': damage_count, 'contacts_count': contacts_count,
               'crawlers': crawlers}
    return render(request, 'administrator/dashboard.html', context)


@user_passes_test(lambda u: u.is_superuser or u.groups.filter(Q(name='employee1') | Q(name='employee2')).count() > 0)
def search_car(request):
    if request.method == 'POST':
        # Remove car temporary
        if request.POST['action'] == 'remove_temp':
            car = Car.objects.get(vin__iexact=request.POST['vin'])
            car.is_it_available = False
            car.available_on_mo = False
            car.available_on_bg = False
            car.available_on_ove = False
            car.available_on_ade = False
            car.save()
        elif request.POST['action'] == 'remove_perm':
            car = Car.objects.get(vin__iexact=request.POST['vin'])
            car.removed_permanently = True
            car.save()
        elif request.POST['action'] == 'clear_remove_perm':
            car = Car.objects.get(vin__iexact=request.POST['vin'])
            car.removed_permanently = False
            car.save()
        elif request.POST['action'] == 'remain_perm':
            car = Car.objects.get(vin__iexact=request.POST['vin'])
            car.remain_permatently = True
            car.save()
        elif request.POST['action'] == 'clear_remain_perm':
            car = Car.objects.get(vin__iexact=request.POST['vin'])
            car.remain_permatently = False
            car.save()

    mo = os.environ.get('MO_URL', '')
    bg = os.environ.get('BG_URL', '')
    ove = os.environ.get('OVE_URL', '')
    ade = os.environ.get('ADE_URL', '')

    context = {'mo': mo, 'bg': bg, 'ove': ove, 'ade': ade}

    if 'stock_number' in request.GET:
        try:
            car = Car.objects.available_cars().get(stock_number__iexact=request.GET['stock_number'])
            context['car'] = car
        except:
            pass
    elif 'id' in request.GET:
        try:
            car = Car.objects.get(id=request.GET['id'])
            context['car'] = car
        except:
            pass
    elif 'vin' in request.GET:
        try:
            car = Car.objects.get(vin=request.GET['vin'])
            context['car'] = car
        except:
            pass

    return render(request, 'administrator/search_car.html', context)


@user_passes_test(lambda u: u.is_superuser or u.groups.filter(Q(name='employee1') | Q(name='employee2')).count() > 0)
def contacts(request):
    contacts = Contact.objects.all().order_by('-id')
    context = {'contacts': contacts}
    return render(request, 'administrator/contacts.html', context)


@user_passes_test(lambda u: u.is_superuser)
def actions(request):
    if request.method == 'POST':
        if 'action' in request.POST:
            if request.POST['action'] == 'calculate_mo_prices':
                # Celery Task
                calculate_mo_prices.delay()
            elif request.POST['action'] == 'calculate_bg_prices':
                # Celery Task
                calculate_bg_prices.delay()
            elif request.POST['action'] == 'calculate_ove_prices':
                # Celery Task
                calculate_ove_prices.delay()
            elif request.POST['action'] == 'calculate_ade_prices':
                # Celery Task
                calculate_ade_prices.delay()
            elif request.POST['action'] == 'mo_all':
                # Celery Task
                mo_all.delay()
            elif request.POST['action'] == 'bg_all':
                # Celery Task
                bg_all.delay()
            elif request.POST['action'] == 'ove_all':
                # Celery Task
                ove_all.delay()
            elif request.POST['action'] == 'ade_all':
                # Celery Task
                ade_all.delay()

    context = {}
    return render(request, 'administrator/actions.html', context)


@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='employee1').count() > 0)
def fill_damages(request):
    run_celery = False

    if request.method == 'POST':

        if request.POST['consider_damage'] == '1':
            part = '(?i)^(' + re.escape(request.POST['part'].lower()) + ')$'
        else:
            part = '.*'

        if request.POST['consider_condition'] == '1':
            temp_cond = re.escape(request.POST['condition'].lower())
            if temp_cond == 'scraped' or temp_cond == 'heavy\\ scratch' or temp_cond == 'scratch\\ heavy' or temp_cond == 'environmental\\ paint\\ dmg' or temp_cond == 'scratched':
                temp_cond = 'scraped|heavy\\ scratch|scratch\\ heavy|environmental\\ paint\\ dmg|scratched'

            condition = '(?i)^(' + temp_cond + ')$'
        else:
            condition = '.*'

        if request.POST['consider_severity'] == '1':
            if request.POST['severity_type'] == 'text':
                severity = '(?i)^(' + re.escape(request.POST['severity'].lower()) + ')$'
            elif request.POST['severity_type'] == 'number':
                severity = request.POST['severity_number']

                if request.POST['number_operation'] == 'G':
                    severity += '<'
                elif request.POST['number_operation'] == 'GE':
                    severity += '<='
                elif request.POST['number_operation'] == 'L':
                    severity += '>'
                elif request.POST['number_operation'] == 'LE':
                    severity += '>='

            elif request.POST['severity_type'] == 'inch':
                severity = request.POST['severity_inch'] + '"'

                if request.POST['inch_operation'] == 'G':
                    severity += '<'
                elif request.POST['inch_operation'] == 'GE':
                    severity += '<='
                elif request.POST['inch_operation'] == 'L':
                    severity += '>'
                elif request.POST['inch_operation'] == 'LE':
                    severity += '>='
        else:
            severity = '.*'

        print part
        print condition
        print severity
        print request.POST['price']

        damage_rule = DamageRule()
        damage_rule.part = part
        damage_rule.condition = condition
        damage_rule.severity = severity
        # Skip car model
        damage_rule.price = int(request.POST['price'])
        damage_rule.mannual = True
        damage_rule.save()

        call_command('calculate_final_prices', 'single', damagerule=damage_rule.id, car=request.POST['car_id'])

        run_celery = True

        #     if key.isdigit() and len(value) > 0 and value.isdigit():
        #         damage = Damage.objects.get(id=key)
        #         damage.estimated_price = value
        #         damage.mannual = True
        #         damage.save()

    damage_count = Damage.objects.filter(car__is_it_available=True, car__is_rejected=False,
                                         car__eligible_to_display=False, estimated_price__isnull=True,
                                         car__make__is_visible=True).count()
    cars = Car.objects.available_cars().filter(is_rejected=False, eligible_to_display=False)

    if run_celery == True:
        # Celery Task
        apply_damage_rule.delay(damage_rule.id)

    context = {'cars': cars, 'damage_count': damage_count}
    return render(request, 'administrator/fill_damages.html', context)


@user_passes_test(lambda u: u.is_superuser or u.groups.filter(Q(name='employee1') | Q(name='employee2')).count() > 0)
def car_list(request):
    if 'site' in request.GET:
        if request.GET['site'] == 'mo' or request.GET['site'] == 'inventory1':
            cars = Car.objects.available_cars().filter(Q(mo_car_id__isnull=False) & (
                Q(available_on_mo=True) | (
                    Q(remain_until__isnull=False) & Q(remain_until__gt=timezone.now())) | Q(remain_permatently=True))).order_by('-created_at')
        elif request.GET['site'] == 'bg' or request.GET['site'] == 'inventory2':
            cars = Car.objects.available_cars().filter(Q(bg_car_id__isnull=False) & (
                Q(available_on_bg=True) | (
                    Q(remain_until__isnull=False) & Q(remain_until__gt=timezone.now())) | Q(remain_permatently=True))).order_by('-created_at')
        elif request.GET['site'] == 'ove' or request.GET['site'] == 'inventory3':
            cars = Car.objects.available_cars().filter(Q(ove_car_id__isnull=False) & (
                Q(available_on_ove=True) | (
                    Q(remain_until__isnull=False) & Q(remain_until__gt=timezone.now())) | Q(remain_permatently=True) )).order_by('-created_at')
        elif request.GET['site'] == 'ade' or request.GET['site'] == 'inventory4':
            cars = Car.objects.available_cars().filter(Q(ade_car_id__isnull=False) & (
                Q(available_on_ade=True) | (
                    Q(remain_until__isnull=False) & Q(remain_until__gt=timezone.now())) | Q(remain_permatently=True) )).order_by('-created_at')
    else:
        return HttpResponse('A problem occurred.')

    context = {'cars': cars}
    return render(request, 'administrator/car_list.html', context)


@user_passes_test(lambda u: u.is_superuser or u.groups.filter(Q(name='employee1') | Q(name='employee2')).count() > 0)
def stock_images(request):
    if request.method == 'POST':
        stock_image = StockImage()
        stock_image.image = request.FILES['image']
        stock_image.view_type = request.POST['image_view']
        stock_image.save()

        color_ids = request.POST.getlist('colors')
        for color_id in color_ids:
            color = Color.objects.get(id=color_id)
            stock_image.colors.add(color)

        years = request.POST.getlist('years')

        if request.POST['model'] != '-1':
            for year in years:
                stock_image_info = StockImageInfo()
                stock_image_info.stock_image = stock_image
                car_model = CarModel.objects.get(id=request.POST['model'])
                stock_image_info.model = car_model
                stock_image_info.trim = None
                stock_image_info.year = int(year)
                stock_image_info.save()
        else:
            car_trim_ids = request.POST.getlist('trims')
            for car_trim_id in car_trim_ids:
                car_trim = CarTrim.objects.get(id=car_trim_id)

                for year in years:
                    stock_image_info = StockImageInfo()
                    stock_image_info.stock_image = stock_image
                    stock_image_info.model = car_trim.model
                    stock_image_info.trim = car_trim
                    stock_image_info.year = int(year)
                    stock_image_info.save()

    car_models = CarModel.objects.all()
    car_trims = CarTrim.objects.all()

    years = [2017, 2016, 2015, 2014, 2013]

    colors = Color.objects.all()
    image_views = [('F', 'FRONT'), ('B', 'BACK'), ('S', 'SIDE')]

    context = {'car_models': car_models, 'car_trims': car_trims, 'years': years, 'colors': colors,
               'image_views': image_views}

    return render(request, 'administrator/stock_images.html', context)
