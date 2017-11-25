# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand
from django.core.management import call_command

import os

from os import listdir
from os.path import isfile, join, exists

from bs4 import NavigableString, Tag

from crawler.management.common import *
from crawler.models import *

URL = os.environ.get('OVE_URL', '')

data_dir = 'crawler/management/data/ove/'
headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:49.0) Gecko/20100101 Firefox/49.0',
    'Host': 'www.' + URL,
    'X-Requested-With': 'XMLHttpRequest'
}

headers_manheim = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36',
    'Host': 'mmsc400.manheim.com',
    'Upgrade-Insecure-Requests': '1'
}

headers_carfax = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, sdch, br',
    'Accept-Language': 'en-US,en;q=0.8,fa;q=0.6,de;q=0.4',
    'Connection': 'keep-alive',
    'Host': 'secured.carfax.com',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36'
}

ove_location_dict = {'CA - Manheim Riverside': 'Manheim Riverside', 'WA - Manheim Seattle': 'Manheim Seattle',
                     'NV - Manheim Nevada': 'Manheim Nevada',
                     'CA - Manheim San Francisco Bay': 'Manheim San Francisco Bay'}

session = requests.session()


def parse_first_page(text):
    soup = BeautifulSoup(text, 'html.parser')
    authenticity_token = soup.select('[name=authenticity_token]')[0]['value']
    return authenticity_token


def parse_search_page_get_authenticity_token(text):
    soup = BeautifulSoup(text, 'html.parser')
    authenticity_token = soup.select('[name=authenticity_token]')[1]['value']
    return authenticity_token


def parse_search_result():
    '''parse search result to retrieve list of cars'''

    new_dir = data_dir + folder_name + '/'
    onlyfiles = [f for f in listdir(new_dir) if isfile(join(new_dir, f))]

    all_car_info = []

    for result_file in onlyfiles:
        if not result_file.endswith('.html'):
            continue

        soup = BeautifulSoup(open(new_dir + result_file), 'html.parser')

        cars_elements = soup.select('.veh-row')

        car_info = []

        for i in range(len(cars_elements)):
            car_element = cars_elements[i]
            vin = car_element.select('.veh-vin')[0].string  # VIN
            try:
                car_id = car_element.select('.vdpLink')[0]['href'].split('show/')[1]  # Retrieve car id
            except:
                print "ERROR, cannot retrieve car_id", car_element
                continue
            price = None
            price_elements = car_element.select('.veh-price span')
            if len(price_elements) == 1:
                price = price_elements[0].string.strip().split('$')[1].replace(',', '')

            # grade_elements = car_element.select('.icon-grade')
            # if len(grade_elements) > 0:
            #     grade = grade_elements[0].text
            #     if float(grade) < 2: # OVE GRADE RESTRICTION. TODO: make it parameter
            #         continue
            # else:
            #     continue

            car_info.append({'car_id': car_id, 'VIN': vin, 'price': price})

        # print car_info
        # print len(car_info)
        # print '====='
        all_car_info.extend(car_info)
    return all_car_info


def login():
    global session

    username = os.environ.get('OVE_USERNAME', '')
    password = os.environ.get('OVE_PASSWORD', '')

    url = 'https://www.' + URL

    login_url = 'https://www.' + URL + '/authenticate'

    # ========= 1 Visit first page

    p = session.get(url, headers=headers)
    authenticity_token = parse_first_page(p.text)

    login_data = {
        'user[username]': username,
        'user[password]': password,
        'commit': 'Login',
        'utf8': '%E2%9C%93',
        'authenticity_token': authenticity_token
    }

    # ========= 2 login

    p = session.post(login_url, data=login_data, headers=headers)  # post login data

    print 'login'
    print p.status_code

    wait_about(30)


def fetch_search_results():
    new_dir = data_dir + str(timezone.localtime(timezone.now()).year) + '-' + str(
        timezone.localtime(timezone.now()).month) + '-' + str(
        timezone.localtime(timezone.now()).day) + '-' + str(timezone.localtime(timezone.now()).hour) + '/'

    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    # Visit
    p = session.get('https://www.' + URL)

    print 'visit search page'
    print p.status_code

    wait_about(30)

    authenticity_token = parse_search_page_get_authenticity_token(p.text)
    search_url = 'https://www.' + URL + '/search/results'

    # Fake Search, then update that
    print 'Performing fake search'

    search_data = [
        ('utf8', '%E2%9C%93'),
        ('authenticity_token', authenticity_token),
        ('criteria[vehicle_type_id]', 'Passenger'),
        ('criteria[make_id]', '7'),
        ('criteria[search_model_id]', '184330'),
        ('criteria[start_year]', '2013'),
        ('criteria[end_year]', ''),
        ('criteria[vin]', ''),
        ('criteria[seller_name]', ''),
        ('criteria[distance]', ''),
        ('criteria[distance_unit]', ''),
        ('criteria[zip_code]', ''),
        ('criteria[facilitation_service_provider_id][]', '39'),
        ('criteria[facilitation_service_provider_id][]', '95'),
        ('criteria[facilitation_service_provider_id][]', '133'),
        ('criteria[facilitation_service_provider_id][]', '634'),
        ('criteria[facilitation_service_provider_id][]', '15'),
        ('criteria[facilitation_service_provider_id][]', '19'),
        ('sellers[select]', 'All Sellers'),
        ('search_type', 'basic'),
        ('commit', 'Search'),
    ]

    p = session.post(search_url, data=search_data, headers=headers)

    print p.status_code

    wait_about(30)

    # Update search
    print 'Updating Search options...'

    authenticity_token = parse_search_page_get_authenticity_token(p.text)

    update_search_url = 'https://www.' + URL + '/search/filter/update_search'

    # update make models
    update_data = [
        ('utf8', '%E2%9C%93'),
        ('authenticity_token', authenticity_token),
        ('target_attribute', 'search_model_id'),
        ('presenter[search_model_id][]', '184330'),
        ('presenter[search_model_id][]', '188512'),
        ('presenter[search_model_id][]', '184333'),
        ('presenter[search_model_id][]', '188166'),
        ('presenter[search_model_id][]', '184336'),
        ('presenter[search_model_id][]', '184338'),
        ('presenter[search_model_id][]', '11282'),
        ('presenter[search_model_id][]', '68'),
        ('presenter[search_model_id][]', '69'),
        ('presenter[search_model_id][]', '4472'),
        ('presenter[search_model_id][]', '184340'),
        ('presenter[search_model_id][]', '189948'),
    ]

    p = session.post(update_search_url, data=update_data, headers=headers)

    f = open(new_dir + 'result1.html', 'w')
    f.write(p.text.encode('utf-8'))
    f.close()
    print 'page 1 fetched'

    if not is_last_search_page(p.text):

        wait_about(40)

        page = 2
        while page <= 15:  # set max = 15
            next_page_url = 'https://www.' + URL + '/search/results?WT.svl=o_ove_srp_next&page=' + str(page)
            p = session.get(next_page_url, headers=headers)

            f = open(new_dir + 'result' + str(page) + '.html', 'w')
            f.write(p.text.encode('utf-8'))
            f.close()

            print 'page ' + str(page) + ' fetched'

            if is_last_search_page(p.text):
                break

            wait_about(60)
            page += 1


def is_last_search_page(text):
    soup = BeautifulSoup(text, 'html.parser')

    x = soup.select('.display_count')[0].string.strip()
    num1 = x.split('- ')[1].split(' of ')[0]
    num2 = x.split('- ')[1].split(' of ')[1].split(' ')[0]

    if num1 == num2:
        return True
    return False


def fetch_vehicle_details(car_id, car_vin):
    '''Fetch vehicle details page'''

    new_dir = data_dir + folder_name + '/' + 'car_details/'

    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    should_wait = False

    # Fetch Vehicle Details
    car_detail_path = new_dir + 'car_' + str(car_id) + '.html'

    if exists(car_detail_path):
        print 'Fetched before'
    else:
        print 'Fetching ', car_id
        fetch_vehicle_details_url = 'https://www.' + URL + '/vdp/show/' + str(car_id)
        p = session.get(fetch_vehicle_details_url, headers=headers)
        print p.status_code
        f = open(car_detail_path, 'w')
        f.write(p.text.encode('utf-8'))
        f.close()
        should_wait = True
        wait_about(1, 1)

    fetch_vehicle_CR_url = parse_get_CR_link(car_id)

    # Fetch Condition Report
    CR_path = new_dir + 'car_CR_' + str(car_id) + '.html'
    if exists(CR_path):
        print 'Condition Report Fetched Before'
    else:
        print 'Fetching ', car_id, 'Condition Report'

        if fetch_vehicle_CR_url != None:
            p = session.get(fetch_vehicle_CR_url, headers=headers_manheim)
            print p.status_code
            if p.status_code == 200:
                f = open(CR_path, 'w')
                f.write(p.text.encode('utf-8'))
                f.close()
            wait_about(1, 1)
        else:
            print '=========> Does not find condition report for ', car_id

    # Fetch Carfax
    carfax_link = 'https://secured.carfax.com/auction-partner/continue-as-dealer.cfx?vin=' + car_vin + '&partner=OVE&cfxUsername=C581680&buyerId=dolceluxuryimports'
    carfax_path = new_dir + 'car_carfax_' + str(car_id) + '.html'

    if exists(carfax_path):
        print 'Carfax Fetched Before'
    else:
        print 'Fetching ', car_id, 'Carfax'

        if carfax_link != None:
            p = session.get(carfax_link, headers=headers_carfax)
            print p.status_code
            if p.status_code == 200:
                f = open(carfax_path, 'w')
                f.write(p.text.encode('utf-8'))
                f.close()

            should_wait = True
        else:
            print '=========> Does not find carfax for ', car_id

    if should_wait == True:
        wait_about(30, 30)


def parse_get_CR_link(car_id):
    new_dir = data_dir + folder_name + '/' + 'car_details/'
    filename = 'car_' + str(car_id) + '.html'
    soup = BeautifulSoup(open(new_dir + filename), 'html.parser')

    cr_link = None

    try:
        cr_link = soup.select('.icon-cr')[0]['href'].split('&username')[0]
    except:
        pass

    return cr_link


def parse_vehicle_condition_report_page(car_id):
    filename = 'car_CR_' + str(car_id) + '.html'
    new_dir = data_dir + folder_name + '/' 'car_details/'
    soup = BeautifulSoup(open(new_dir + filename), 'html.parser')

    ans = {}

    ################ Value Added Options ################
    value_added_options = []
    value_added_options_elements = soup.select('#highValueOptions .mainfont .mainfont')
    for value_added_options_element in value_added_options_elements:
        p = value_added_options_element.contents
        i = 0
        while i < len(p):
            next = p[i]
            while next != None:
                if isinstance(next, NavigableString):
                    if len(next.strip()) > 0:
                        value_added_options.append(next.strip())
                    next = next.nextSibling
                elif isinstance(next, Tag):
                    p = next.contents
                    i = -1
                    break
            i += 1

    ans['value_added_options'] = value_added_options

    ################ Vehicle Information ################

    options = []
    vehicle_information_elements = soup.select('#vehicleInformation .mainfont td.mainfont')
    for vehicle_information_element in vehicle_information_elements:
        p = vehicle_information_element.contents
        i = 0
        while i < len(p):
            next = p[i]
            while next != None:
                if isinstance(next, NavigableString):
                    if len(next.strip()) > 0:
                        options.append(next.strip())
                    next = next.nextSibling
                elif isinstance(next, Tag):
                    p = next.contents
                    i = -1
                    break
            i += 1

    ans['options'] = options

    ################ Damages ################

    vehicle_damage_elements = soup.select('#categoryFound')
    damages = []
    for vehicle_damage_element in vehicle_damage_elements:
        td_set = vehicle_damage_element.select('td.mainfont')
        damage = []
        for i in range(len(td_set)):
            td = td_set[i]
            if td.string == None:
                damage.append('')
            else:
                damage.append(td.string.strip())
        damages.append(damage)
    ans['damages'] = damages

    grade_elements = soup.select('.gradeValue')
    if len(grade_elements) > 0:
        grade = grade_elements[0].text[1:]
        ans['grade'] = float(grade)

    return ans


def parse_vehicle_detail_page(car_id):
    filename = 'car_' + str(car_id) + '.html'
    new_dir = data_dir + folder_name + '/' 'car_details/'
    soup = BeautifulSoup(open(new_dir + filename), 'html.parser')

    ans = {}

    ###########################

    if len(soup.select('#listing_description_id')) == 0:
        print "Service Temporarily Unavailable!!"
        return

    year, model = soup.select('#listing_description_id')[0].string.strip().split(' ', 1)
    price = None
    price_element = soup.select('#buy_now_amount')
    # if len(price_element) > 0:
    #     price_element = soup.select('#buy_now_amount')

    image_list = []
    images = soup.find("div", {"id": "carouselContain"})
    if images != None:
        images = images.findAll("li", {"class": "gallery_thumb"})
        for i in images:
            try:
                myLink = i.find("a")["href"]
                image_list.append(myLink)
            except:
                print str(i) + " is not a correct href"
    ans["images"] = image_list

    if len(price_element) > 0:
        price = price_element[0].string.strip().split('$')[1].replace(',', '')

    ans['price'] = price
    ans['year'] = year
    ans['make'], ans['model'] = model.split(' ', 1)
    ############################
    spec = soup.find("div", {"id": "listing_specifications"})
    specs_keys = map(lambda x: x.getText(), spec.findAll("th"))
    specs_val = map(lambda x: x.getText(), spec.findAll("td"))
    for i in range(len(specs_keys)):
        mykey = str(specs_keys[i][:-1])
        ans[mykey] = specs_val[i]
    ############################
    facts = soup.find("div", {"id": "vehicle_facts"})
    facts = facts.findAll("div", {"class": "mui-row-no-m"})
    facts = facts[1]
    facts_keys = facts.findAll("dt")
    facts_val = facts.findAll("dd")
    ans["location"] = facts_val[2].getText()
    colors = facts_val[1].getText().split("/")
    ans["exterior"] = colors[0]
    ans["interior"] = colors[1]
    # print facts_val[1].getText().split("/")
    # print facts_val[2].getText()

    # print ans

    ############# Grade #############

    grade_elements = soup.select('.icon-grade')
    if len(grade_elements) > 0:
        grade = grade_elements[0].text
        ans['grade'] = float(grade)

    return ans


def get_latest_search_folder_name():
    folders = [f for f in listdir(data_dir)]
    latest = None
    for f in folders:
        if not os.path.isdir(data_dir + f):
            continue
        t = map(int, f.split('-'))
        if latest == None:
            latest = t
        elif t[0] > latest[0] \
                or (t[0] == latest[0] and t[1] > latest[1]) \
                or (t[0] == latest[0] and t[1] == latest[1] and t[2] > latest[2]) \
                or (t[0] == latest[0] and t[1] == latest[1] and t[2] == latest[2] and t[3] > latest[3]):
            latest = t

    if latest == None:
        return None
    return '-'.join(map(str, latest))


def get_car_lists_for_different_actions(all_car_info):
    should_fetch = []
    should_remove = []
    should_update_price = []
    should_update_id = []

    cars = Car.objects.filter(ove_car_id__isnull=False, available_on_ove=True, is_it_available=True)

    remove_count = 0
    update_count = 0
    new_count = 0
    rep = 0

    # TODO: do it in log(n), not n^2
    for car in cars:
        find = False
        for car_info in all_car_info:
            if car_info['VIN'] == str(car.vin):
                if car_info['car_id'] != car.ove_car_id:
                    should_update_id.append(car_info)

                if str(car_info['price']) != str(car.original_price):
                    print 'price: ', str(car.original_price), '------->', car_info['price']
                    # Price has been changed. Should get updated
                    update_count += 1
                    if car_info['price'] != None and car.original_price != None and abs(
                                    car.original_price - int(car_info['price'])) <= 700:
                        should_update_price.append(car_info)
                    else:
                        should_fetch.append(car_info)
                else:
                    rep += 1

                find = True
                break

        if find == False:
            # Doesn't found anymore. Remove it from database
            remove_count += 1
            should_remove.append(car.vin)

    for car_info in all_car_info:
        find = False
        for car in cars:
            if car_info['VIN'] == str(car.vin):
                find = True
                break

        if find == False:
            new_count += 1
            should_fetch.append(car_info)

    print 'remove', remove_count, 'cars'
    print 'should update', update_count, 'cars'
    print 'should add', new_count, 'cars'
    print 'repetitive ', rep, 'cars'
    return should_fetch, should_remove, should_update_price, should_update_id


def get_bmw_model_and_trim(title):
    models = CarModel.objects.filter(make__name='BMW')

    my_model = None
    my_trim = None

    found = False
    for model in models:
        if model.name.lower() in title.lower():
            found = True
            if my_model == None or len(model.name) > len(my_model.name):
                my_model = model

    if found == False:
        if 'z series' in title.lower():
            my_model = CarModel.objects.get(name='Z4')

    if my_model != None:
        trims = CarTrim.objects.filter(model__name__iexact=my_model.name)

        found = False
        for trim in trims:
            if trim.name.lower() in title.lower():
                found = True
                my_trim = trim
                break

    return my_model, my_trim


def search_process():
    login()
    fetch_search_results()


def fetch_cars_process():
    # Analyze results and fetch car details
    all_car_info = parse_search_result()
    should_fetch, should_remove, should_update_price, should_update_id = get_car_lists_for_different_actions(
        all_car_info)

    # login()
    for i in range(len(should_fetch)):
        try:
            fetch_vehicle_details(should_fetch[i]['car_id'], should_fetch[i]['VIN'])
        except:
            print 'Error occured in fetch_vehicle_details of ove car ', should_fetch[i]['car_id']

    return should_remove, should_update_price, should_update_id


def update_db_process(should_remove, should_update_price, should_update_id):
    new_dir = data_dir + folder_name + '/' + 'car_details/'

    print '=====> Remove not available cars (OVE)'

    for car_vin in should_remove:
        car = Car.objects.get(vin=car_vin)
        car.available_on_ove = False
        car.ove_removed_at = timezone.localtime(timezone.now())

        if car.available_on_mo == False and car.available_on_bg == False and car.available_on_ove == False and car.available_on_ade == False:
            car.is_it_available = False

        car.save()
        print 'Remove ', car_vin

    print '=====> End Removing'

    print '=====> Update Car Prices'
    print should_update_price
    for car_info in should_update_price:
        car = Car.objects.get(vin=car_info['VIN'])
        last_price = car.original_price
        car.original_price = car_info['price']
        car.available_on_ove = True
        car.is_it_available = True
        car.save()
        print 'Update ', car_info['car_id'], 'Price ', last_price, '-->', car_info['price']

    print '=====> End Updating Prices'

    print '=====> Update Car IDs'
    print should_update_id
    for car_info in should_update_id:
        car = Car.objects.get(vin=car_info['VIN'])
        last_id = car.ove_car_id
        car.ove_car_id = car_info['car_id']
        car.save()
        print 'Update ', car_info['car_id'], 'ID ', last_id, '-->', car_info['car_id']

    print '=====> End Updating IDs'

    if not exists(new_dir):
        return

    onlyfiles = [f for f in listdir(new_dir) if isfile(join(new_dir, f))]

    for car_detail_file in onlyfiles:
        if not car_detail_file.endswith('.html'):
            continue
        if car_detail_file.startswith('car_CR'):
            continue
        if car_detail_file.startswith('car_carfax'):
            continue

        car_id = car_detail_file.split('.')[0].split('_')[1]
        print '======================='
        print car_id

        car_condition_filename = car_detail_file.replace('car', 'car_CR')
        if not car_condition_filename in onlyfiles:
            print 'Doest not have condition report'
            continue

        carfax_exist = True
        carfax_filename = 'car_carfax_' + str(car_id) + '.html'
        carfax_path = data_dir + folder_name + '/' + 'car_details/' + carfax_filename
        if not carfax_filename in onlyfiles:
            print 'Does not have carfax'
            carfax_exist = False
            # continue

        print 'Start reading car page'
        try:
            car_info = parse_vehicle_detail_page(car_id)
        except:
            print 'Error Occured in parsing car page', car_id
            continue
        print 'Reading car page is finished'

        print 'Start reading car condition'
        try:
            car_CR = parse_vehicle_condition_report_page(car_id)
        except:
            print 'Error Occured in parsing condition report', car_id
            continue
        print 'reading car condition is finished'

        carfax = None
        if carfax_exist == True:
            print 'Start reading car carfax'
            try:
                car_carfax_info = parse_carfax(carfax_path)
                carfax = get_carfax_object(car_carfax_info)  # carfax object without car set
            except:
                print 'Error Occured in parsing carfax', car_id
                # continue
            print 'reading car carfax is finished'

        updating = False

        try:
            car = Car.objects.get(vin=car_info['VIN'])
            car.last_updated_time = timezone.localtime(timezone.now())
            car.is_rejected = False
            car.eligible_to_display = False

            updating = True

            print 'UPDATIIIIIIIIIIIIIIIIIIIIIIIIIIIIING CAR'
        except:
            print 'NEWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW CAR'
            car = Car()

        car.available_on_ove = True
        car.is_it_available = True
        car.vin = car_info['VIN']
        car.ove_car_id = car_id
        car.car_model = car_info['model']
        car.last_checking = timezone.localtime(timezone.now())
        car.original_price = car_info['price']
        car.year = car_info['year']

        my_model, my_trim = get_bmw_model_and_trim(car_info['model'])
        car.model = my_model
        car.trim = my_trim

        if 'grade' in car_info:
            car.grade = float(car_info['grade'])
        elif 'grade' in car_CR:
            car.grade = float(car_CR['grade'])
        else:
            car.grade = None

        # Location
        try:
            ove_location = ove_location_dict[car_info['location']]
            location = Location.objects.get(name__iexact=ove_location)
            car.location = location
            # print location.name
        except:
            print 'Location is not in database -------->' + car_info['location']

        make = Make.objects.get(name__iexact=car_info['make'])
        car.make = make

        # set carfax car attr
        if carfax != None and hasattr(car, 'carfax'):
            car.carfax = carfax

        car.save()

        # set carfax car attr
        if carfax != None and hasattr(car, 'carfax') == False:
            carfax.car = car
            carfax.save()

        try:
            car_detail = CarDetail.objects.get(car=car)
        except CarDetail.DoesNotExist:
            car_detail = CarDetail(car=car)

        car_detail.detail_html = new_dir + car_detail_file
        car_detail.vehicle_options = '\n'.join(car_CR['options'])
        car_detail.miles = car_info['Odometer'].split(' ')[0].replace(',', '')
        # car_detail.exterior = car_info['exterior']
        # car_detail.interior = car_info['interior']
        # car_detail.engine = car_info['engine']
        # car_detail.odor = car_info['odor'] if 'odor' in car_info else None
        # car_detail.msrp = car_info['msrp']
        # car_detail.announcements = car_info['announcements']
        car_detail.value_added_options = ', '.join(car_CR['value_added_options'])
        # car_detail.drive = car_info['drive']
        # # car_detail.keys = car_info[''],
        #
        # if len(car_info['warranty date']) > 0:
        #     date_set = car_info['warranty date'].split('-')
        #     warranty_date = '20' + date_set[2] + '-' + date_set[0] + '-' + date_set[1]
        #     car_detail.warranty_date = warranty_date

        car_detail.save()

        # # Repairs
        # if 'repairs' in car_info:
        #     repairs = Repair.objects.filter(car=car)
        #     repairs.delete()
        #
        #     for ans_item in car_info['repairs']:
        #         repair = Repair(car=car)
        #         repair.repaired = ans_item[0]
        #         repair.condition = ans_item[1]
        #         repair.severity = ans_item[2]
        #         repair.repair_type = ans_item[3]
        #         repair.save()

        # Damages
        if 'damages' in car_CR:
            damages = Damage.objects.filter(car=car)
            damages.delete()

            for ans_item in car_CR['damages']:
                damage = Damage(car=car)
                damage.part = ans_item[1]
                damage.condition = ans_item[2]
                damage.severity = ans_item[3]
                damage.save()

        if updating == False:
            # Images
            if 'images' in car_info:
                images = Image.objects.filter(car=car)

                for image_link in car_info['images']:
                    if not Image.objects.filter(link=image_link).exists():
                        image = Image(car=car)
                        image.link = image_link
                        image.save()


class Command(BaseCommand):
    help = 'Crawl ' + URL

    def add_arguments(self, parser):
        parser.add_argument('type', type=str)

    def change_crawler_status(self, status):
        self.ove_crawler.status = status
        if status == "RUNNING":
            self.ove_crawler.last_run = timezone.now()
        self.ove_crawler.save()

    def handle(self, *args, **options):
        global folder_name

        self.ove_crawler = Crawler.objects.get(name="ove")

        try:
            if options['type'] == 'all':
                self.change_crawler_status("RUNNING")

                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)

                # Start Process

                print "-------> OVE"

                # Search
                print "===================== Start Search Process ====================="
                search_process()
                print "===================== End Search Process ====================="

                folder_name = get_latest_search_folder_name()
                print folder_name

                # Analyze results and fetch car details
                print "===================== Start Fetch Cars Process ====================="
                should_remove, should_update_price, should_update_id = fetch_cars_process()
                print "===================== End Fetch Cars Process ====================="

                # Update DB
                print "===================== Start Update DB Process ====================="
                update_db_process(should_remove, should_update_price, should_update_id)
                print "===================== End Update DB Process ====================="

                # Calculate Prices
                print "===================== Start Calculate Final Prices Process ====================="
                call_command('calculate_final_prices', 'ove_cars')
                print "===================== End Calculate Final Prices Process ====================="

            elif options['type'] == 'fetch':
                self.change_crawler_status("RUNNING")

                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)

                # Start Process

                print "-------> OVE"

                # Search
                print "===================== Start Search Process ====================="
                search_process()
                print "===================== End Search Process ====================="

                folder_name = get_latest_search_folder_name()
                print folder_name

                # Analyze results and fetch car details
                print "===================== Start Fetch Cars Process ====================="
                should_remove, should_update_price, should_update_id = fetch_cars_process()
                print "===================== End Fetch Cars Process ====================="

            elif options['type'] == 'load':
                self.change_crawler_status("RUNNING")

                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)

                # Start Process

                print "-------> OVE"

                folder_name = get_latest_search_folder_name()
                print folder_name

                all_car_info = parse_search_result()
                should_fetch, should_remove, should_update_price, should_update_id = get_car_lists_for_different_actions(
                    all_car_info)

                # Update DB
                print "===================== Start Update DB Process ====================="
                update_db_process(should_remove, should_update_price, should_update_id)
                print "===================== End Update DB Process ====================="

                # Calculate Prices
                print "===================== Start Calculate Final Prices Process ====================="
                call_command('calculate_final_prices', 'ove_cars')
                print "===================== End Calculate Final Prices Process ====================="
        finally:
            self.change_crawler_status("IDLE")
