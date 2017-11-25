# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

import requests.utils
import os, sys, re

from os import listdir
from os.path import isfile, join, exists

from crawler.management.common import *
from crawler.models import *

URL = os.environ.get('MO_URL', '')

data_dir = 'crawler/management/data/mo/'
headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.8,fa;q=0.6,de;q=0.4',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Host': URL
}

headers_carfax = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, sdch, br',
    'Accept-Language': 'en-US,en;q=0.8,fa;q=0.6,de;q=0.4',
    'Connection': 'keep-alive',
    'Host': 'secured.carfax.com',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36'
}

folder_name = None
session = None

def fetch_vehicle_details(last_url, car_id, car_vin):
    '''Fetch car details page'''

    new_dir = data_dir + folder_name + '/' + 'car_details/'

    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    should_wait = False

    # Fetch Vehicle Details
    if exists(new_dir + 'car_' + str(car_id) + '.html'):
        print 'Fetched before'
    else:
        print 'Fetching ', car_id
        fetch_vehicle_details_url = last_url + '&_eventId=fetchVehicleDetails&vehicleId=' + str(car_id) + '&saleId=0'
        p = session.get(fetch_vehicle_details_url, headers=headers)
        print p.status_code
        f = open(new_dir + 'car_' + str(car_id) + '.html', 'w')
        f.write(p.text.encode('utf-8'))
        should_wait = True
        wait_about(3, 3)

    # Fetch Carfax
    carfax_link = 'https://' + URL + '/AIMS-Web/carfax.go?VIN=' + car_vin + '&loginId=SH.Bolandparvaz'
    carfax_path = new_dir + 'car_carfax_' + str(car_id) + '.html'
    if exists(carfax_path):
        print 'Carfax Fetched Before'
    else:
        print 'Fetching ', car_id, 'Carfax'

        if carfax_link != None:
            p = session.get(carfax_link, headers=headers)
            carfax_link = parse_get_main_carfax_link(p.text.encode('utf-8'))
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
        wait_about(20, 20)  # Fetch Vehicle Detail Pages Time Gap


def parse_get_main_carfax_link(html_text):
    return html_text[1:-1]


def parse_vehicle_detail_page(car_id):
    ''' miles, options, details, damages, repairs, keys, images, prices '''
    filename = 'car_' + str(car_id) + '.html'
    new_dir = data_dir + folder_name + '/' + 'car_details/'
    soup = BeautifulSoup(open(new_dir + filename), 'html.parser')

    ans = {}

    try:
        miles_element = soup.select('#miles-value')[0]
        miles = miles_element.string.strip().replace(',', '').split(' ')[0]
        # print miles
        ans['miles'] = miles
    except KeyboardInterrupt:
        sys.exit()
    except:
        ans['miles'] = None

    vehicle_options_element = soup.select('.vehicle-options-table td')
    vehicle_options = []
    for v in vehicle_options_element:
        vehicle_options.append(v.string.strip())
    ans['options'] = vehicle_options

    vehicle_details_elements = soup.select('.vehicle-details-table')
    vehicle_details_element = vehicle_details_elements[0]
    ans['year'], ans['trim'] = vehicle_details_element.select('.caption-header-left')[0].string.strip().encode(
        'utf-8').split(chr(194) + chr(160))

    ans['grade'] = vehicle_details_element.select('.caption-header-right')[0].string.strip().split(' ')[1]

    t = re.search('([A-Za-z]+)([0-9A-Za-z]+)', ans['trim'], re.IGNORECASE)
    ans['model'] = t.group(1)

    vehicle_details_element = vehicle_details_elements[1]
    td_set = vehicle_details_element.select('td')

    # vin
    # location
    # miles
    # exterior
    # title state --> not used
    # interior
    # warranty date
    # engine
    # drive
    # odor
    # msrp
    # announcements
    # value added options

    for td in td_set:
        if len(td) == 0:
            continue
        title = td.select('span')[0].string.strip()[:-1]
        title = title.lower()
        # print title

        if title == 'miles':
            continue

        value = ' '.join(td.contents[1].strip().split()) if len(td.contents) > 1 else ''

        if title == 'msrp':
            value = value.split('$')[1].replace(',', '')

        # print value
        # print '====='

        ans[title] = value

    vehicle_condition_elements = soup.select('.vehicle-condition-table')

    for vehicle_condition_element in vehicle_condition_elements:
        table_title = vehicle_condition_element.select('thead tr th')[0].string.strip()
        if table_title == 'Damages':
            tr_set = vehicle_condition_element.select('tbody tr')
            damages = []
            for tr in tr_set:
                td_set = tr.select('td')
                damage = []
                for td in td_set:
                    if td.string == None:
                        damage.append('')
                    else:
                        damage.append(td.string.strip())
                damages.append(damage)
            # print damages
            ans['damages'] = damages

        elif table_title == 'Repaired':
            tr_set = vehicle_condition_element.select('tbody tr')
            repairs = []
            for tr in tr_set:
                td_set = tr.select('td')
                repair = []
                for td in td_set:
                    if td.string != None:
                        repair.append(td.string.strip())
                    else:
                        repair.append("")
                repairs.append(repair)
            # print repairs
            ans['repairs'] = repairs

        elif table_title == 'Key':
            tr_set = vehicle_condition_element.select('tbody tr')
            keys = []
            for tr in tr_set:
                td_set = tr.select('td')
                key = []
                for td in td_set:
                    key.append(td.string.strip())
                keys.append(key)
            # print keys
            ans['keys'] = keys

    images = set()
    image_elements = soup.select('#links img.image-padding')
    for image_element in image_elements:
        images.add(image_element['src'])
    # print '\n'.join(images)
    ans['images'] = list(images)
    price_elements = soup.select('.label-buy-search-newprice')

    if len(price_elements) == 0:
        price_elements = soup.select('.label-buy-search')

    if len(price_elements) == 0:
        ans['price'] = None
    else:
        price_element = price_elements[0]
        price = price_element.string.strip().split('$')[1].replace(',', '')
        # print price
        ans['price'] = price

    return ans


def parse_search_result():
    '''parse search result to retrieve list of cars and their ID, VIN, and price'''

    new_dir = data_dir + folder_name + '/'

    onlyfiles = [f for f in listdir(new_dir) if isfile(join(new_dir, f))]

    all_car_info = []

    for result_file in onlyfiles:
        if not result_file.endswith('.html'):
            continue

        soup = BeautifulSoup(open(new_dir + result_file), 'html.parser')

        cars_elements = soup.select('a[title="Vehicle details"]')
        car_info = []

        for i in range(len(cars_elements)):
            car_element = cars_elements[i]
            VIN = car_element.parent.select('span')[0].string  # VIN
            car_id = car_element['href'].split('\'')[1]  # Retrieve car id
            price = None

            price_elements = car_element.parent.parent.select('.label-buy-search-newprice')
            if len(price_elements) == 0:
                price_elements = car_element.parent.parent.select('.label-buy-search')

            if len(price_elements) == 1:
                price = price_elements[0].string.strip().split('$')[1].replace(',', '')
            else:
                price_elements = car_element.parent.parent.select('.label-my-activity-buy')
                for index, price_element in enumerate(price_elements):
                    if price_element.string.strip() == 'Add Watchlist':
                        continue

                    try:
                        price = price_element.string.strip().split('$')[1].replace(',', '')
                    except KeyboardInterrupt:
                        sys.exit()
                    except:
                        price = None

                    break

            if price != None:
                car_info.append({'car_id': car_id, 'vin': VIN, 'price': price})

        all_car_info.extend(car_info)

    return all_car_info


def login():
    global session

    username = os.environ.get('MO_USERNAME', '')
    password = os.environ.get('MO_PASSWORD', '')

    url = 'http://' + URL

    login_url = 'https://' + URL + '/AIMS-Web/dealerHomePageView'

    login_data = {
        'userName': username,
        'password': password
    }

    # ========= 1 login

    session = requests.session()
    session.get(url, headers=headers)  # visit main page
    p = session.post(login_url, data=login_data, headers=headers)  # post login data

    print 'login'
    print p.status_code

    return p.url


def advanced_search(last_url):
    new_dir = data_dir + str(timezone.localtime(timezone.now()).year) + '-' + str(
        timezone.localtime(timezone.now()).month) + '-' + str(
        timezone.localtime(timezone.now()).day) + '-' + str(timezone.localtime(timezone.now()).hour) + '/'

    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    advanced_search = last_url + '&_eventId=searchCriteria'

    wait_about(30)

    p = session.get(advanced_search, headers=headers)  # visit advanced search page
    print p.status_code
    print 'advance search page visited'

    wait_about(20)

    # post advanced search
    advanced_search_url = p.url + '&_eventId=searchResults&dealerSearchType=ADVANCEDSEARCH'

    advanced_search_data = [
        ('inputRequest.pagingContext.currentPageNo', '1'),
        ('inputRequest.pagingContext.recordsPerPg', '100'),
        ('inputRequest.pagingContext.relatedRecordsPerPage', '100'),
        ('inputRequest.pagingContext.method', 'getPage'),
        ('inputRequest.sortBy', 'VIN_ASC'),
        ('isSearchByVin', ''),
        ('inputRequest.auctionProviders', 'ade'),
        ('_inputRequest.auctionProviders', 'on'),
        ('inputRequest.auctionProviders', 'Manheim'),
        ('_inputRequest.auctionProviders', 'on'),
        ('inputRequest.vehicleClasses', 'B'),
        ('inputRequest.vehicleClasses', 'C'),
        ('inputRequest.vehicleClasses', 'CL'),
        ('inputRequest.vehicleClasses', 'CLA'),
        ('inputRequest.vehicleClasses', 'CLS'),
        ('inputRequest.vehicleClasses', 'E'),
        ('inputRequest.vehicleClasses', 'GL'),
        ('inputRequest.vehicleClasses', 'GLA'),
        ('inputRequest.vehicleClasses', 'GLE'),
        ('inputRequest.vehicleClasses', 'GLK'),
        ('inputRequest.vehicleClasses', 'M'),
        ('inputRequest.vehicleClasses', 'ML'),
        ('inputRequest.vehicleClasses', 'P'),
        ('inputRequest.vehicleClasses', 'S'),
        ('inputRequest.vehicleClasses', 'SL'),
        ('inputRequest.vehicleClasses', 'SLK'),
        ('selectItem', 'B'),
        ('selectItem', 'C'),
        ('selectItem', 'CL'),
        ('selectItem', 'CLA'),
        ('selectItem', 'CLS'),
        ('selectItem', 'E'),
        ('selectItem', 'GL'),
        ('selectItem', 'GLA'),
        ('selectItem', 'GLE'),
        ('selectItem', 'GLK'),
        ('selectItem', 'M'),
        ('selectItem', 'ML'),
        ('selectItem', 'P'),
        ('selectItem', 'S'),
        ('selectItem', 'SL'),
        ('selectItem', 'SLK'),
        ('_inputRequest.vehicleClasses', '1'),
        ('_inputRequest.models', '1'),
        ('inputRequest.fromYear', '2014'),
        ('inputRequest.toYear', 'ALL'),
        ('inputRequest.mileageFrom', ''),
        ('inputRequest.mileageTo', ''),
        # ('inputRequest.grades', '2'),
        ('inputRequest.grades', ''),
        ('inputRequest.grades', ''),
        ('inputRequest.bidreadyChannel', 'BIDREADY'),
        ('_inputRequest.bidreadyChannel', 'on'),
        ('inputRequest.physicalChannel', 'PHYSICAL'),
        ('_inputRequest.physicalChannel', 'on'),
        ('inputRequest.liveSaleChannel', 'LIVESALE'),
        ('_inputRequest.liveSaleChannel', 'on'),
        ('inputRequest.catalogChannel', 'CATALOG'),
        ('_inputRequest.catalogChannel', 'on'),
        ('_inputRequest.exteriorColors', '1'),
        ('_inputRequest.interiorColors', '1'),
        ('inputRequest.locations', '2146105'),
        ('inputRequest.locations', '2147946'),
        ('inputRequest.locations', '276'),
        ('inputRequest.locations', '32'),
        ('inputRequest.locations', '2141993'),
        ('inputRequest.locations', '2130892'),
        ('inputRequest.locations', '2139229'),
        ('inputRequest.locations', '101583'),
        ('inputRequest.locations', '101588'),
        ('inputRequest.locations', '36'),
        ('selectItem', '2146105'),
        ('selectItem', '2147946'),
        ('selectItem', '276'),
        ('selectItem', '32'),
        ('selectItem', '2141993'),
        ('selectItem', '2130892'),
        ('_inputRequest.locations', '1'),
        ('inputRequest.carfax', 'G'),
        ('_inputRequest.carfax', 'on'),
        ('_inputRequest.inventoryNewToMeExists', 'on'),
        ('_inputRequest.cpoReadyOnly', 'on'),
        ('inputRequest.amgSportPackage', ''),
        ('inputRequest.amgWheelPackage', ''),
        ('inputRequest.designoPackage', ''),
        ('inputRequest.sportPackage', ''),
        ('inputRequest.sportSedan', ''),
        ('inputRequest.sportAppearancePackage', ''),
        ('_inputRequest.titleStates', '1'),
        ('inputRequest.blindSpotAssist', ''),
        ('inputRequest.distronic', ''),
        ('inputRequest.distronicPlus', ''),
        ('inputRequest.laneKeepAssist', ''),
        ('inputRequest.nightViewAssist', ''),
        ('inputRequest.nightViewAssistPlus', ''),
        ('inputRequest.parkingGuidance', ''),
        ('inputRequest.parktronic', ''),
        ('inputRequest.rearViewMonitor', ''),
        ('inputRequest.electricTrunkClose', ''),
        ('inputRequest.keylessGo', ''),
        ('inputRequest.powerLiftgate', ''),
        ('inputRequest.heatedSeatsFront', ''),
        ('inputRequest.heatedSeatsRear', ''),
        ('inputRequest.multiContourSeats', ''),
        ('inputRequest.rearSeatPackage', ''),
        ('inputRequest.ventilatedSeatsFront', ''),
        ('inputRequest.ventilatedSeatsRear', ''),
        ('inputRequest.magicSkyControlRoof', ''),
        ('inputRequest.panorama', ''),
        ('inputRequest.navigationExists', 'false'),
        ('inputRequest.entertainmentExists', 'false'),
        ('inputRequest.climateControlExists', 'false'),
        ('_inputRequest.saleDates', '1'),
    ]

    p = session.post(advanced_search_url, data=advanced_search_data, headers=headers)
    print p.status_code
    print '========'

    f = open(new_dir + 'result1.html', 'w')
    f.write(p.text.encode('utf-8'))
    f.close()

    if not is_last_search_page(p.text):

        wait_about(20)

        page = 1
        while page <= 10:  # set max = 10
            next_page_url = p.url + '&_eventId=handlePagination&method=getNext&currentPage=' + str(
                page) + '&relatedmethod=none&relatedcurrentPage=1'
            p = session.get(next_page_url, headers=headers)
            print p.status_code
            print '========'
            f = open(new_dir + 'result' + str(page + 1) + '.html', 'w')
            f.write(p.text.encode('utf-8'))
            f.close()

            if is_last_search_page(p.text):
                break

            wait_about(20)
            page += 1

    return p.url


def is_last_search_page(text):
    soup = BeautifulSoup(text, 'html.parser')
    num1 = soup.select('.exact-matches')[0].string.strip().split('-')[1]
    num2 = soup.select('.header-badge')[0].string.strip()

    if num1 == num2:
        return True
    return False


def temp_search(last_url):
    advanced_search = last_url + '&_eventId=searchCriteria'

    wait_about(40)

    p = session.get(advanced_search, headers=headers)  # visit advanced search page
    print p.status_code

    wait_about(20)

    # post advanced search
    advanced_search_url = p.url + '&_eventId=searchResults&dealerSearchType=ADVANCEDSEARCH'

    advanced_search_data = {
        'inputRequest.pagingContext.currentPageNo': '1',
        'inputRequest.pagingContext.recordsPerPg': '25',
        'inputRequest.pagingContext.relatedRecordsPerPage': '25',
        'inputRequest.pagingContext.method': 'getPage',
        'inputRequest.sortBy': 'VIN_ASC',
        'isSearchByVin': '',
        'inputRequest.auctionProviders': 'ade',
        '_inputRequest.auctionProviders': 'on',
        'inputRequest.auctionProviders': 'Manheim',
        '_inputRequest.auctionProviders': 'on',
        '_inputRequest.vehicleClasses': '1',
        'inputRequest.models': 'C250W',
        'selectItem': 'C250W',
        '_inputRequest.models': '1',
        'inputRequest.fromYear': '2014',
        'inputRequest.toYear': 'ALL',
        'inputRequest.mileageFrom': '',
        'inputRequest.mileageTo': '',
        'inputRequest.grades': '',
        'inputRequest.grades': '',
        'inputRequest.bidreadyChannel': 'BIDREADY',
        '_inputRequest.bidreadyChannel': 'on',
        'inputRequest.physicalChannel': 'PHYSICAL',
        '_inputRequest.physicalChannel': 'on',
        'inputRequest.liveSaleChannel': 'LIVESALE',
        '_inputRequest.liveSaleChannel': 'on',
        'inputRequest.catalogChannel': 'CATALOG',
        '_inputRequest.catalogChannel': 'on',
        '_inputRequest.exteriorColors': '1',
        '_inputRequest.interiorColors': '1',
        'inputRequest.locations': '2141993',
        'selectItem': '2141993',
        '_inputRequest.locations': '1',
        '_inputRequest.carfax': 'on',
        '_inputRequest.inventoryNewToMeExists': 'on',
        '_inputRequest.cpoReadyOnly': 'on',
        'inputRequest.amgSportPackage': '',
        'inputRequest.amgWheelPackage': '',
        'inputRequest.designoPackage': '',
        'inputRequest.sportPackage': '',
        'inputRequest.sportSedan': '',
        'inputRequest.sportAppearancePackage': '',
        '_inputRequest.titleStates': '1',
        'inputRequest.blindSpotAssist': '',
        'inputRequest.distronic': '',
        'inputRequest.distronicPlus': '',
        'inputRequest.laneKeepAssist': '',
        'inputRequest.nightViewAssist': '',
        'inputRequest.nightViewAssistPlus': '',
        'inputRequest.parkingGuidance': '',
        'inputRequest.parktronic': '',
        'inputRequest.rearViewMonitor': '',
        'inputRequest.electricTrunkClose': '',
        'inputRequest.keylessGo': '',
        'inputRequest.powerLiftgate': '',
        'inputRequest.heatedSeatsFront': '',
        'inputRequest.heatedSeatsRear': '',
        'inputRequest.multiContourSeats': '',
        'inputRequest.rearSeatPackage': '',
        'inputRequest.ventilatedSeatsFront': '',
        'inputRequest.ventilatedSeatsRear': '',
        'inputRequest.magicSkyControlRoof': '',
        'inputRequest.panorama': '',
        'inputRequest.navigationExists': 'false',
        'inputRequest.entertainmentExists': 'false',
        'inputRequest.climateControlExists': 'false',
        '_inputRequest.saleDates': '1'
    }

    p = session.post(advanced_search_url, data=advanced_search_data, headers=headers)
    print p.status_code

    wait_about(20)

    return p.url


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

    cars = Car.objects.filter(mo_car_id__isnull=False, available_on_mo=True, is_it_available=True)

    remove_count = 0
    update_count = 0
    new_count = 0
    rep = 0

    # TODO: do it in log(n), not n^2
    for car in cars:
        find = False
        for car_info in all_car_info:
            if car_info['vin'] == str(car.vin):
                if str(car_info['price']) != str(car.original_price):
                    print str(car.original_price), '------->', car_info['price']
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
            remove_count += 1
            should_remove.append(car.vin)

    for car_info in all_car_info:
        find = False
        for car in cars:
            if car_info['vin'] == str(car.vin):
                find = True
                break

        if find == False:
            new_count += 1
            should_fetch.append(car_info)

    print 'remove', remove_count, 'cars'
    print 'should update', update_count, 'cars'
    print 'should add', new_count, 'cars'
    print 'repetitive ', rep, 'cars'
    return should_fetch, should_remove, should_update_price


def search_process():
    last_url = login()
    last_url = advanced_search(last_url)

    return last_url


def fetch_cars_process(last_url):
    all_car_info = parse_search_result()
    should_fetch, should_remove, should_update_price = get_car_lists_for_different_actions(all_car_info)

    # last_url = login()
    last_url = temp_search(last_url)  # Fake search to get permission to see cars
    for i in range(len(should_fetch)):
        try:
            fetch_vehicle_details(last_url, should_fetch[i]['car_id'], should_fetch[i]['vin'])
        except KeyboardInterrupt:
            sys.exit()
        except:
            print 'Error occured in fetch_vehicle_details of mo car ', should_fetch[i]['car_id']

    return should_remove, should_update_price


def update_db_process(should_remove, should_update_price):
    new_dir = data_dir + folder_name + '/' + 'car_details/'

    print '=====> Remove not available cars (mo)'

    for car_vin in should_remove:
        car = Car.objects.get(vin=car_vin)
        car.available_on_mo = False
        car.mo_removed_at = timezone.localtime(timezone.now())

        if car.available_on_mo == False and car.available_on_bg == False and car.available_on_ove == False and car.available_on_ade == False:
            car.is_it_available = False

        car.save()
        print 'Remove ', car_vin

    print '=====> End Removing'

    print '=====> Update Car Prices'
    print should_update_price
    for car_info in should_update_price:
        car = Car.objects.get(vin=car_info['vin'])
        last_price = car.original_price
        car.original_price = car_info['price']
        car.available_on_mo = True
        car.is_it_available = True
        car.save()
        print 'Update ', car_info['car_id'], 'Price ', last_price, '-->', car_info['price']

    print '=====> End Updating Prices'

    if not exists(new_dir):
        return

    onlyfiles = [f for f in listdir(new_dir) if isfile(join(new_dir, f))]

    for car_detail_file in onlyfiles:
        if not car_detail_file.endswith('.html'):
            continue
        if car_detail_file.startswith('car_carfax'):
            continue

        car_id = car_detail_file.split('.')[0].split('_')[1]
        print '======================='
        print car_id

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
        except KeyboardInterrupt:
            sys.exit()
        except:
            print 'Error Occured in parsing car page'
            continue

        print 'Reading car page is finished'

        carfax = None
        if carfax_exist == True:
            print 'Start reading car carfax'
            try:
                car_carfax_info = parse_carfax(carfax_path)
                carfax = get_carfax_object(car_carfax_info)  # carfax object without car set
            except KeyboardInterrupt:
                sys.exit()
            except:
                print 'Error Occured in parsing carfax'
                # Normally we should continue, but because search in mo is on clean carfax, lets read it
                # continue
            print 'Reading car carfax is finished'

        try:
            car = Car.objects.get(vin=car_info['vin'])
            car.last_updated_time = timezone.localtime(timezone.now())
            car.is_rejected = False
            car.eligible_to_display = False
            print 'UPDATIIIIIIIIIIIIIIIIIIIIIIIIIIIIING CAR'
        except KeyboardInterrupt:
            sys.exit()
        except:
            print 'NEWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW CAR'
            car = Car()

        car.available_on_mo = True
        car.is_it_available = True
        car.vin = car_info['vin']
        car.mo_car_id = car_id
        car.car_model = car_info['trim']

        car_model = CarModel.objects.filter(name=car_info['model']).first()
        car_trim = CarTrim.objects.filter(name=car_info['trim']).first()

        car.model = car_model
        car.trim = car_trim

        car.last_checking = timezone.localtime(timezone.now())
        car.original_price = car_info['price']
        car.year = car_info['year']

        # Location
        try:
            location = Location.objects.get(name__iexact=car_info['location'])
            car.location = location
            # print location.name
        except KeyboardInterrupt:
            sys.exit()
        except:
            print 'Location is not in database -------->' + car_info['location']

        try:
            car.grade = float(car_info['grade'])
        except KeyboardInterrupt:
            sys.exit()
        except:
            pass

        make = Make.objects.get(name='Mercedes Benz')
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
        except KeyboardInterrupt:
            sys.exit()
        except CarDetail.DoesNotExist:
            car_detail = CarDetail(car=car)

        car_detail.detail_html = new_dir + car_detail_file
        car_detail.vehicle_options = '\n'.join(car_info['options'])
        car_detail.miles = car_info['miles']
        car_detail.exterior = car_info['exterior']
        car_detail.interior = car_info['interior']
        car_detail.engine = car_info['engine']
        car_detail.odor = car_info['odor'] if 'odor' in car_info else None
        car_detail.msrp = car_info['msrp']
        car_detail.announcements = car_info['announcements']
        car_detail.value_added_options = car_info['value added options']
        car_detail.drive = car_info['drive']
        # car_detail.keys = car_info[''],

        if len(car_info['warranty date']) > 0:
            date_set = car_info['warranty date'].split('-')
            warranty_date = '20' + date_set[2] + '-' + date_set[0] + '-' + date_set[1]
            car_detail.warranty_date = warranty_date

        car_detail.save()

        # Repairs
        if 'repairs' in car_info:
            repairs = Repair.objects.filter(car=car)
            repairs.delete()

            for ans_item in car_info['repairs']:
                repair = Repair(car=car)
                repair.repaired = ans_item[0]
                repair.condition = ans_item[1]
                repair.severity = ans_item[2]
                repair.repair_type = ans_item[3]
                repair.save()

        # Damages
        if 'damages' in car_info:
            damages = Damage.objects.filter(car=car)
            damages.delete()

            for ans_item in car_info['damages']:
                damage = Damage(car=car)
                damage.part = ans_item[0]
                damage.condition = ans_item[1]
                damage.severity = ans_item[2]
                damage.save()

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
        self.mo_crawler.status = status
        if status == "RUNNING":
            self.mo_crawler.last_run = timezone.now()
        self.mo_crawler.save()

    def handle(self, *args, **options):
        global folder_name

        self.mo_crawler = Crawler.objects.get(name="mo")

        try:
            if options['type'] == 'all':
                self.change_crawler_status("RUNNING")

                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)

                # Start Process

                print "-------> mo"

                # Search
                print "===================== Start Search Process ====================="
                last_url = search_process()
                print "===================== End Search Process ====================="

                folder_name = get_latest_search_folder_name()
                print folder_name

                # Analyze results and fetch car details
                print "===================== Start Fetch Cars Process ====================="
                should_remove, should_update_price = fetch_cars_process(last_url)
                print "===================== End Fetch Cars Process ====================="

                # Update DB
                print "===================== Start Update DB Process ====================="
                update_db_process(should_remove, should_update_price)
                print "===================== End Update DB Process ====================="

                # Calculate Prices
                print "===================== Start Calculate Final Prices Process ====================="
                call_command('calculate_final_prices', 'mo_cars')
                print "===================== End Calculate Final Prices Process ====================="

            elif options['type'] == 'fetch':
                self.change_crawler_status("RUNNING")

                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)

                # Start Process

                print "-------> mo"

                # Search
                print "===================== Start Search Process ====================="
                last_url = search_process()
                print "===================== End Search Process ====================="

                folder_name = get_latest_search_folder_name()
                print folder_name

                # Analyze results and fetch car details
                print "===================== Start Fetch Cars Process ====================="
                should_remove, should_update_price = fetch_cars_process(last_url)
                print "===================== End Fetch Cars Process ====================="

            elif options['type'] == 'load':
                self.change_crawler_status("RUNNING")

                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)

                # Start Process

                print "-------> mo"

                folder_name = get_latest_search_folder_name()
                print folder_name

                # Analyze results and fetch car details
                all_car_info = parse_search_result()
                should_fetch, should_remove, should_update_price = get_car_lists_for_different_actions(all_car_info)

                # Update DB
                print "===================== Start Update DB Process ====================="
                update_db_process(should_remove, should_update_price)
                print "===================== End Update DB Process ====================="

                # Calculate Prices
                print "===================== Start Calculate Final Prices Process ====================="
                call_command('calculate_final_prices', 'mo_cars')
                print "===================== End Calculate Final Prices Process ====================="
        finally:
            self.change_crawler_status("IDLE")
