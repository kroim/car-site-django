from django.shortcuts import redirect, render

from crawler.models import *
from main.models import *

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q

from templatetags.int_tags import thousands_separator, human_format
from templatetags.normalize_price import normalize_price

from django_ajax.decorators import ajax

from django.template import Context
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse

from django.contrib.auth import login, logout, authenticate
#from django.contrib.auth.forms import UserCreationForm

from main.forms import UserCreationFormWithEmail
from main.forms import SimpleUserCreationFormWithEmail
from main.forms import SimpleUserLoginFormWithEmail
from itertools import chain
from django.contrib.auth.models import User

import os
import smtplib
import time
import re
import imaplib
import email
from email.utils import parseaddr
from zopy.crm import CRM

def car_browse(request):
    context = {}
    page = None
    if request.method == 'POST':
        page = request.POST.get('page')

    cars = Car.objects.available_eligible_cars()

    makes = Make.objects.filter(is_visible=True)
    make_options = []
    for make in makes:
        make_count = cars.filter(make=make).count()
        make_options.append([make.name, False, make_count])

    year_options = [['2017', False], ['2016', False], ['2015', False], ['2014', False], ['2013', False]]

    if 'price' in request.GET:
        if len(request.GET['price']) > 0 and not request.GET['price'][-1] == '+':
            cars = cars.filter(final_price__lte=request.GET['price'])
    if 'milage' in request.GET:
        if len(request.GET['milage']) > 0 and not request.GET['milage'][-1] == '+':
            cars = cars.filter(cardetail__miles__lte=request.GET['milage'])
    if 'year' in request.GET:
        year_list = request.GET.getlist('year')

        if not 'all' in year_list and len(year_list) > 0:
            year_condition = None
            for year in year_list:
                filter(lambda x: x[0] == year, year_options)[0][1] = True
                if year_condition == None:
                    year_condition = Q(year=year)
                else:
                    year_condition = year_condition | Q(year=year)
            cars = cars.filter(year_condition)
    if 'make' in request.GET:
        make_list = request.GET.getlist('make')

        if not 'all' in make_list and len(make_list) > 0:
            make_condition = None
            for make_name in make_list:
                try:
                    filter(lambda x: x[0] == make_name, make_options)[0][1] = True
                    make = Make.objects.get(name=make_name, is_visible=True)
                except:
                    continue
                if make_condition == None:
                    make_condition = Q(make=make)
                else:
                    make_condition = make_condition | Q(make=make)

            if make_condition != None:
                cars = cars.filter(make_condition)
            else:
                cars = Car.objects.none()

        if not 'all' in make_list and len(make_list) > 0:
            try:
                make = Make.objects.get(name__iexact=make_list[0], is_visible=True)
            except:
                make = None
            model_options = CarModel.objects.filter(make=make)
            context['model_options'] = model_options

    if 'model' in request.GET and request.GET['model'] != 'all':
        cars = cars.filter(model__name__iexact=request.GET['model'], model__make__is_visible=True)

    if 'sort' in request.GET:
        if request.GET['sort'] == 'price-inc':
            cars = cars.order_by('final_price')
        if request.GET['sort'] == 'price-dec':
            cars = cars.order_by('-final_price')
        if request.GET['sort'] == 'mileage-inc':
            cars = cars.order_by('cardetail__miles')
        if request.GET['sort'] == 'mileage-dec':
            cars = cars.order_by('-cardetail__miles')

    paginator = Paginator(cars, 12)

    try:
        cars = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        cars = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        cars = paginator.page(paginator.num_pages)

    context['cars'] = cars
    context['make_options'] = make_options
    context['year_options'] = year_options
    if os.environ.get("CARBOI_ENV", "development") == "development":
        context['fuel_api_key'] = 'daefd14b-9f2b-4968-9e4d-9d4bb4af01d1'
    else:
        context['fuel_api_key'] = '5b676744-d22d-4e48-b14a-c6f75c8742ff'

    return render(request, 'main/car_browse.html', context)


@ajax
def ajax_load_cars(request):
    if request.method == 'POST':
        if 'page' in request.POST:

            context = {}
            page = request.POST['page']

            cars = Car.objects.available_eligible_cars().values('id', 'vin', 'final_price', 'year',
                                                                'cardetail__exterior', 'model__name', 'make__name',
                                                                'model__fuel_name', 'make__fuel_name', 'car_model',
                                                                'cardetail__miles', 'unique_customer_link')

            if 'price' in request.GET:
                if len(request.GET['price']) > 0 and not request.GET['price'][-1] == '+':
                    cars = cars.filter(final_price__lte=request.GET['price'])
            if 'milage' in request.GET:
                if len(request.GET['milage']) > 0 and not request.GET['milage'][-1] == '+':
                    cars = cars.filter(cardetail__miles__lte=request.GET['milage'])
            if 'year' in request.GET:
                year_list = request.GET.getlist('year')

                if not 'all' in year_list and len(year_list) > 0:
                    year_condition = None
                    for year in year_list:
                        if year_condition == None:
                            year_condition = Q(year=year)
                        else:
                            year_condition = year_condition | Q(year=year)
                    cars = cars.filter(year_condition)
            if 'make' in request.GET:
                make_list = request.GET.getlist('make')

                if not 'all' in make_list and len(make_list) > 0:
                    make_condition = None
                    for make_name in make_list:
                        try:
                            make = Make.objects.get(name=make_name, is_visible=True)
                        except:
                            continue
                        if make_condition == None:
                            make_condition = Q(make=make)
                        else:
                            make_condition = make_condition | Q(make=make)

                    if make_condition != None:
                        cars = cars.filter(Q(make__is_visible=True) & make_condition)
                    else:
                        cars = Car.objects.none()

                if not 'all' in make_list and len(make_list) > 0:
                    try:
                        make = Make.objects.get(name__iexact=make_list[0], is_visible=True)
                    except:
                        make = None
                    model_options = CarModel.objects.filter(make=make)
                    context['model_options'] = model_options

            if 'model' in request.GET and request.GET['model'] != 'all':
                cars = cars.filter(model__name__iexact=request.GET['model'], model__make__is_visible=True)

            if 'sort' in request.GET:
                if request.GET['sort'] == 'price-inc':
                    cars = cars.order_by('final_price')
                if request.GET['sort'] == 'price-dec':
                    cars = cars.order_by('-final_price')
                if request.GET['sort'] == 'mileage-inc':
                    cars = cars.order_by('cardetail__miles')
                if request.GET['sort'] == 'mileage-dec':
                    cars = cars.order_by('-cardetail__miles')

            paginator = Paginator(cars, 12)

            try:
                cars = paginator.page(page)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                return {}
            except EmptyPage:
                # If page is out of range (e.g. 9999), deliver last page of results.
                return {}

            cars_list = list(cars)

            for i in xrange(len(cars)):
                car = Car.objects.get(id=cars_list[i]['id'])
                cars_list[i]['stock_image'] = car.stock_image()
                cars_list[i]['cardetail__miles'] = human_format(cars_list[i]['cardetail__miles'])
                cars_list[i]['final_price'] = thousands_separator(normalize_price(cars_list[i]['final_price']))

            context['cars'] = cars_list

            return context

    return {}


@ajax
def ajax_load_models(request):
    if request.method == 'POST' and 'make' in request.POST:
        if request.POST['make'] != 'all':
            models = CarModel.objects.values('id', 'name').filter(make__name=request.POST['make'],
                                                                  make__is_visible=True)
            return {'models': models}
    return {}


def home_page(request):
    makes = Make.objects.filter(is_visible=True)
    years = ['2017', '2016', '2015', '2014', '2013']

    context = {'makes': makes, 'years': years}
    return render(request, 'main/home_page.html', context)


def car_profile(request, car_id):
    context = {}
    if request.method == 'POST':
        if loginShowroom(request, car_id):
            return redirect('/showroom/' + car_id)
            car = Car.objects.get(id=request.POST['car_id'])
            contact = Contact()
            contact.car = car
            contact.first_name = request.POST['first_name']
            contact.last_name = request.POST['last_name']
            contact.phone_number = request.POST['phone']
            contact.email = request.POST['email']
            contact.comment = request.POST['comment']
            contact.save()
            context['show_toast'] = True

            ### Sending email
            plaintext = get_template('main/email/request_detail.txt')
            htmly = get_template('main/email/request_detail.html')
            d = Context({'first_name': request.POST['first_name'], 'last_name': request.POST['last_name'],
                         'phone_number': request.POST['phone'], 'email': request.POST['email'],
                         'comment': request.POST['comment'],
                         'car_link': 'http://carboi.com' + reverse('search_car') + "?id=" + str(car.id)});

            subject, from_email = 'Photo Request', 'Carboi Administrator <noreply@carboi.com>'
            to = 'carboi408@gmail.com <carboi408@gmail.com>'
            text_content = plaintext.render(d)
            html_content = htmly.render(d)

            try:
                msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            except Exception as e:
                print "A problem occured in sending email to you. Please contact administrator."

    car = Car.objects.get(id=car_id)

    similar_cars = Car.objects \
                       .available_eligible_cars() \
                       .extra(select={'dist': 'abs(final_price - ' + str(car.final_price) + ')'}) \
                       .filter(~Q(id=car_id) & Q(make=car.make) & Q(model__isnull=False)) \
                       .order_by('dist')[:4]

    context['car'] = car
    context['similar_cars'] = similar_cars

    vehicle_options = []
    if car.cardetail.vehicle_options != None:
        vehicle_options = car.cardetail.vehicle_options.split('\n')
    context['vehicle_options'] = vehicle_options

    if os.environ.get("CARBOI_ENV", "development") == "development":
        context['fuel_api_key'] = 'daefd14b-9f2b-4968-9e4d-9d4bb4af01d1'
    else:
        context['fuel_api_key'] = '5b676744-d22d-4e48-b14a-c6f75c8742ff'

    return render(request, 'main/car_profile.html', context)


def customer_car_view(request, unique_customer_link):
    if request.method == 'POST':
        if request.user and (request.user.is_superuser or request.user.groups.filter(
                    Q(name='employee1') | Q(name='employee2')).count() > 0):
            image = Image.objects.get(id=request.POST['img_id'])
            if request.POST['action'] == 'add':
                image.show_to_customer = True
            else:
                image.show_to_customer = False
            image.save()

    car = Car.objects.get(unique_customer_link=unique_customer_link)
    vehicle_options = []
    if car.cardetail.vehicle_options != None:
        vehicle_options = car.cardetail.vehicle_options.split('\n')
    context = {'car': car, 'vehicle_options': vehicle_options}
    return render(request, 'main/customer_car_view.html', context)


def buying_process(request):
    context = {}
    return render(request, 'main/buying_process.html', context)


def finance(request):
    context = {}
    return render(request, 'main/finance.html', context)


def about_us(request):
    context = {}
    return render(request, 'main/about_us.html', context)


def faq(request):
    faqs_list = []

    faq_categories = FAQCategory.objects.all()
    for faq_category in faq_categories:
        faqs = FAQ.objects.filter(faq_category=faq_category)
        faqs_list.append((faq_category, faqs))

    context = {'faqs_list': faqs_list}
    return render(request, 'main/faq.html', context)

'''
Displays recommended cars based on user interest.
-5 cars will be top 5 lowest priced cars of same year's model
-3 same model, previous year
-3 same model, next year 
-additional cars in special circumstances for some BMW trims
-up to 5 additional cars if in same year and within +- $1000 if car cost
trim_id's:
428i-trim_id=105
435i-trim_id=107
528i-112
535i-121
328i-89
320i-81
'''
#generates show room based on currently logged in user
def showroom(request, car_id):
    if request.user.is_authenticated():
        print 'logined'
    else:
        return redirect('login')

    context = {}
    additional_cars = []
    user = request.user

    car = Car.objects.get(pk=car_id)
    #relation = UserCarRecommendation(account=user.account, car=car)
    #relation.save()

    #car = user.account.car.all()[0]
    #car_id = car.id

    context['additional_cars'] = ''
    # a mess of epic proportion that pulls additional cars for special circumstances 
    if car.trim and car.trim.name == '528i':
        if car.year == 2015 or car.year == 2016:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id = 121) & (Q(year = car.year) or Q(year = car.year - 1) or Q(year = car.year + 1))) \
                            .order_by('dist')[:3]
        elif car.year == 2014:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id = 121) & (Q(year = car.year) or Q(year = car.year + 1) or Q(year = car.year + 2))) \
                            .order_by('dist')[:3]
        elif car.year == 2017:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id = 121) & (Q(year = car.year) or Q(year = car.year - 1) or Q(year = car.year - 2))) \
                            .order_by('dist')[:3]
        context['additional_cars'] = additional_cars
    elif car.trim and car.trim.name == '535i':
        if car.year == 2015 or car.year == 2016:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id = 112) & (Q(year = car.year) or Q(year = car.year - 1) or Q(year = car.year + 1))) \
                            .order_by('dist')[:3]
        elif car.year == 2014:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id = 112) & (Q(year = car.year) or Q(year = car.year + 1) or Q(year = car.year + 2))) \
                            .order_by('dist')[:3]
        elif car.year == 2017:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id = 112) & (Q(year = car.year) or Q(year = car.year - 1) or Q(year = car.year - 2))) \
                            .order_by('dist')[:3]
        context['additional_cars'] = additional_cars
    elif car.trim and car.trim.name == '435i':
        if car.year == 2015 or car.year == 2016:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id=105) & (Q(year = car.year) or Q(year = car.year - 1) or Q(year = car.year + 1))) \
                            .order_by('dist')[:3]
        elif car.year == 2014:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id=105) & (Q(year = car.year) or Q(year = car.year + 1) or Q(year = car.year + 2))) \
                            .order_by('dist')[:3]
        elif car.year == 2017:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id=105) & (Q(year = car.year) or Q(year = car.year - 1) or Q(year = car.year - 2))) \
                            .order_by('dist')[:3]
        context['additional_cars'] = additional_cars
    elif car.trim and car.trim.name == '428i':
        if car.year == 2015 or car.year == 2016:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id=107) & (Q(year = car.year) or Q(year = car.year - 1) or Q(year = car.year + 1))) \
                            .order_by('dist')[:3]
        elif car.year == 2014:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id=107) & (Q(year = car.year) or Q(year = car.year + 1) or Q(year = car.year + 2))) \
                            .order_by('dist')[:3]
        elif car.year == 2017:
            additional_cars = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(~Q(id=car_id) & Q(trim_id=107) & (Q(year = car.year) or Q(year = car.year + 1) or Q(year = car.year + 2))) \
                            .order_by('dist')[:3]
        context['additional_cars'] = additional_cars

    cars_within_1000 =  Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -' + str(car.final_price)}) \
                            .filter(final_price__range=(car.final_price-1000,car.final_price+1000)) \
                            .order_by('dist')[:5]

    context['additional_cars'] = sorted(chain(additional_cars, cars_within_1000),
                                    key=lambda instance:instance.final_price)
    #context['additional_cars'] = cars_within_1000
    #Generates 3 lists of cars
    if car.year == 2015 or car.year == 2016:
        cars_of_same_year = Car.objects \
                       .available_eligible_cars() \
                       .extra(select={'dist': 'final_price -'  + str(car.final_price)}) \
                       .filter(~Q(id=car_id) & Q(make=car.make) & Q(model = car.model) & Q(year = car.year)) \
                       .order_by('dist')[:5]
        #cars_2 is 2nd list of cars. Generally the cars of the same model in the previous year, except when at an edge case,
        #i.e cars which have come out in current year
        cars_2 = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -'  + str(car.final_price) }) \
                            .filter(~Q(id=car_id) & Q(make=car.make) & Q(model = car.model) & Q(year = car.year - 1)) \
                            .order_by('dist')[:3]
        #cars 3 is 3rd list of cars. Generally the cars of the same model in the next year, except when at an edge case
        cars_3 = Car.objects \
                       .available_eligible_cars() \
                       .extra(select={'dist': 'final_price -'  + str(car.final_price) }) \
                       .filter(~Q(id=car_id) & Q(make=car.make) & Q(model = car.model) & Q(year = car.year + 1)) \
                       .order_by('dist')[:3]

    elif car.year == 2014:
        cars_of_same_year = Car.objects \
                       .available_eligible_cars() \
                       .extra(select={'dist': 'final_price -'  + str(car.final_price)}) \
                       .filter(~Q(id=car_id) & Q(make=car.make) & Q(model = car.model) & Q(year = car.year)) \
                       .order_by('dist')[:5]
        #cars_2 is 2nd list of cars. Generally the cars of the same model in the previous year, except when at an edge case,
        #i.e cars which have come out in current year
        cars_2 = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -'  + str(car.final_price) }) \
                            .filter(~Q(id=car_id) & Q(make=car.make) & Q(model = car.model) & Q(year = car.year + 1)) \
                            .order_by('dist')[:3]
        #cars 3 is 3rd list of cars. Generally the cars of the same model in the next year, except when at an edge case
        cars_3 = Car.objects \
                       .available_eligible_cars() \
                       .extra(select={'dist': 'final_price -'  + str(car.final_price) }) \
                       .filter(~Q(id=car_id) & Q(make=car.make) & Q(model = car.model) & Q(year = car.year + 2)) \
                       .order_by('dist')[:3]



    elif car.year == 2017:
        cars_of_same_year = Car.objects \
                       .available_eligible_cars() \
                       .extra(select={'dist': 'final_price -'  + str(car.final_price)}) \
                       .filter(~Q(id=car_id) & Q(make=car.make) & Q(model = car.model) & Q(year = car.year)) \
                       .order_by('dist')[:5]
        #cars_2 is 2nd list of cars. Generally the cars of the same model in the previous year, except when at an edge case,
        #i.e cars which have come out in current year
        cars_2 = Car.objects \
                            .available_eligible_cars() \
                            .extra(select={'dist': 'final_price -'  + str(car.final_price) }) \
                            .filter(~Q(id=car_id) & Q(make=car.make) & Q(model = car.model) & Q(year = car.year - 1)) \
                            .order_by('dist')[:3]
        #cars 3 is 3rd list of cars. Generally the cars of the same model in the next year, except when at an edge case
        cars_3 = Car.objects \
                       .available_eligible_cars() \
                       .extra(select={'dist': 'final_price -'  + str(car.final_price) }) \
                       .filter(~Q(id=car_id) & Q(make=car.make) & Q(model = car.model) & Q(year = car.year - 2)) \
                       .order_by('dist')[:3]

    '''cars_of_same_year, cars_2, cars_3 are more for development so that it is more visible which cars are being pulled
       context['all_cars'] will contain all the cars being pulled sorted by price'''
    context['car'] = car
    context['cars_of_same_year'] = cars_of_same_year
    context['cars_2'] = cars_2
    context['cars_3'] = cars_3
    context['all_cars'] = sorted(chain(additional_cars, cars_within_1000,cars_of_same_year,cars_2,cars_3),
                                    key=lambda instance:instance.final_price)
    if os.environ.get("CARBOI_ENV", "development") == "development":
        context['fuel_api_key'] = 'daefd14b-9f2b-4968-9e4d-9d4bb4af01d1'
    else:
        context['fuel_api_key'] = '5b676744-d22d-4e48-b14a-c6f75c8742ff'
    return render(request, 'main/showroom.html', context)

def signup(request):
    if request.method == 'POST':
        form = SimpleUserCreationFormWithEmail(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()
            user.account.phone = form.cleaned_data.get('phone')
            user.save()
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username,password=raw_password)
            login(request, user)
            return redirect('home_page')
    else:
        form = SimpleUserCreationFormWithEmail()

    return render(request,'main/signup.html',{'form': form})
ORG_EMAIL   = "@gmail.com"
FROM_EMAIL  = "longhongwang" + ORG_EMAIL
FROM_PWD    = "!@#456gmail"
SMTP_SERVER = "imap.gmail.com"
SMTP_PORT   = 993
def read_email_from_gmail():
    try:
        mail = imaplib.IMAP4_SSL(SMTP_SERVER)
        mail.login(FROM_EMAIL,FROM_PWD)
        mail.select('inbox')

        type, data = mail.search(None, 'ALL')
        mail_ids = data[0]

        id_list = mail_ids.split()
        first_email_id = int(id_list[0])
        latest_email_id = int(id_list[-1])


        for i in range(latest_email_id,first_email_id, -1):
            typ, data = mail.fetch(i, '(RFC822)' )

            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_string(response_part[1])
                    email_from = msg['from']
                    retParse = parseaddr(email_from)
                    print retParse[1]

                    #user = User.objects.create_user(username=retParse[1], password='1', first_name='hello', last_name='test')
                    #user.account.phone = '123456'
                    #user.save

                    authToken = "d84ec22b5689204a4a288a275c675587"
                    crm = CRM(authToken=authToken, scope="ZohoCRM/crmapi")
                    crm_search = crm.searchRecords(module="CustomModule3",
                                                   criteria={"Correo Electronico": "carboi408@gmail.com"})

                    print crm_search.result.CustomModule3.row.FL.custommodule3_id

                    print crm
            break

    except Exception, e:
        print str(e)

def selfLogin(request):
    if request.method == 'POST':
        #read_email_from_gmail()
        username = request.POST.get("username", "")
        raw_password = request.POST.get("password1", "")
        user = authenticate(username=username,password=raw_password)
        if user is not None:
            login(request, user)
            return redirect('home_page')
        else:
            form = SimpleUserLoginFormWithEmail()
    else:
        form = SimpleUserLoginFormWithEmail()

    return render(request,'main/login.html',{'form': form})

def selfLogout(request):
    logout(request)
    return redirect('home_page')

def loginShowroom(request, carId):

    username = request.POST['email']
    fname = request.POST['first_name']
    lname = request.POST['last_name']
    phone = request.POST['phone']

    if username == '':
        return False

    logout(request)
    user = authenticate(username=username, password='1')
    if user != None:
        login(request, user)
    else:
        user = User.objects.create_user(username=username, password='1', first_name=fname, last_name=lname)
        user.account.phone = phone
        user.save
        login(request, user)
    return True

def loginShowroom111(request, carId):
    if request.method == 'POST':
        form = UserCreationFormWithEmail(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()
            user.account.phone = form.cleaned_data.get('phone')
            user.save()
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username,password=raw_password)

            car = Car.objects.get(pk=form.cleaned_data.get('car_id'))
            relation = UserCarRecommendation(account=user.account, car=car)
            relation.save()
            login(request, user)
            return True