# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

import os
import httplib
import socket

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver import remote

from os import listdir
from os.path import isfile, join, exists

from crawler.management.common import *
from crawler.models import *

data_dir = 'crawler/management/data/bg/'

driver = None
URL = os.environ.get('BG_URL', '')

def get_driver_status():
    try:
        driver.execute(remote.command.Command.STATUS)
        return "Alive"
    except httplib.BadStatusLine:
        pass
    except (socket.error, httplib.CannotSendRequest):
        return "Dead"


def parse_vehicle_detail_page(car_id):
    filename = 'car_' + str(car_id) + '.html'
    new_dir = data_dir + folder_name + '/' 'car_details/'
    soup = BeautifulSoup(open(new_dir + filename), 'html.parser')

    ans = {}

    ############### Vehicle Title & VIN & Price ##############

    try:
        title = soup.select('.vehicle-name')[0].text
    except:
        return None

    VIN = soup.select('.vehicle-desc > span')[0].text

    price_digit_elements = soup.select('.odometer-inside .odometer-digit .odometer-digit-inner .odometer-value')

    price = None
    if len(price_digit_elements) > 0:
        price = 0

    for price_digit_element in price_digit_elements:
        price *= 10
        price += int(price_digit_element.text)

    splited_title = title.split(' ')

    ans['title'] = title
    ans['year'] = title.split(' ')[0]
    ans['price'] = price
    ans['vin'] = VIN

    if splited_title[1] == 'MINI':
        ans['make'] = 'MINI'
    else:
        ans['make'] = 'BMW'

    ############### Vehiacle Details ###############

    keys = soup.select('.vehicle-stats dl dt span')
    values = soup.select('.vehicle-stats dl dd span')

    for i in range(len(keys)):
        ans[keys[i].text] = values[i].text

    ############### Vehiacle Images ###############

    image_elements = soup.select('.vehicle-thumb > .mini-slider ul li a img')
    images = map(lambda x: x['src'].replace('_Thumbnail', '_Beautyshot'), image_elements)

    ans['images'] = images

    ############### VEHICLE SPECIFICS ###############

    keys = soup.select('.vehicle-specifications .row dl dt span')
    values = soup.select('.vehicle-specifications .row dl dd span')

    for i in range(len(keys)):
        ans[keys[i].text] = values[i].text

    ############### Announcements ###############

    announcements_element = soup.select('.announcements p span:nth-of-type(2)')
    if len(announcements_element) > 0:
        announcement = announcements_element[0].text
        ans['Announced Conditions'] = announcement

    ############### BUILD DATA ###############

    additional_options_elements = soup.select('#Widget_Packages .row');
    additional_options = []
    if len(additional_options_elements) > 0:
        additional_options_elements = additional_options_elements[-1].select('span')
        if len(additional_options_elements) > 0:
            for additional_options_element in additional_options_elements:
                additional_options.append(additional_options_element.text)
    ans['options'] = additional_options

    ############### EQUIPMENT ###############

    equipment_elements = soup.select('.equipment .row ul li span')
    equipments = map(lambda x: x.text, equipment_elements)
    ans['equipments'] = equipments

    ############### CONDITION REPORT ###############

    keys = soup.select('.condition-information .row dl dt span')
    values = soup.select('.condition-information .row dl dd span')

    for i in range(len(keys)):
        ans[keys[i].text] = values[i].text

    ############### DAMAGE SUMMARY ###############

    damage_elements = soup.select('.damage-summary .damage-entry .row')
    damages = []
    repairs = []
    for damage_element in damage_elements:
        ds = damage_element.select('dl dd span')
        ds_arr = map(lambda x: x.text, ds)
        if ds_arr[-1] == 'N':
            damages.append(ds_arr[:-1])
        else:
            repairs.append(ds_arr[:-1])

    ans['damages'] = damages
    ans['repairs'] = repairs

    ############### TIRES AND WHEELS ###############

    tire_elements = soup.select('.tires-wheels .tire-specs dl')
    tires = []
    for i, tire_element in enumerate(tire_elements):
        if i >= 4:
            # TODO: 4 --> Spare, 5 --> Wheel
            break

        tire = []
        tire.append(tire_element.select('dt span')[0].text)  # Tire type
        ttreads = tire_element.select('dd p:nth-of-type(1) span')

        has_tread = True
        try:
            tire.append(ttreads[0].text + ttreads[1].text)  # Tire tread
        except:
            has_tread = False

        if has_tread == False:
            tire.append(None)
            tire.append(tire_element.select('dd p:nth-of-type(1) span')[0].text)  # Tire Brand
            tire.append(tire_element.select('dd p:nth-of-type(2) span')[0].text)  # Tire size
        else:
            tire.append(tire_element.select('dd p:nth-of-type(2) span')[0].text)  # Tire Brand
            tire.append(tire_element.select('dd p:nth-of-type(3) span')[0].text)  # Tire size

        tires.append(tire)

    ans['tires'] = tires

    return ans


def login():
    driver.get("https://" + URL + "/login?ReturnUrl=%2F")

    delay = 40  # seconds
    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'username')))
        print "See First Page to Login"
    except TimeoutException:
        print "Loading took too much time!"
        # driver.save_screenshot('screenshot.png')
        driver.quit()

    driver.execute_script(
        "ko.dataFor(document.getElementById('username')).username('" + os.environ.get('BG_USERNAME', '') + "');")  # Fill Username using Knockoutjs viewmodel
    driver.execute_script(
        "ko.dataFor(document.getElementById('password')).password('" + os.environ.get('BG_PASSWORD', '') + "');")  # Fill Password using Knockoutjs viewmodel

    driver.execute_script("$('.btn[type=submit]')[0].click()")  # Click on Submit Button

    delay = 40  # seconds
    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'nav-list')))
        print "Login Successfully"
    except TimeoutException:
        print "Loading took too much time!"
        # driver.save_screenshot('screenshot.png')
        driver.quit()

    wait_about(3)


def fetch_search_results():
    new_dir = data_dir + str(timezone.localtime(timezone.now()).year) + '-' + str(
        timezone.localtime(timezone.now()).month) + '-' + str(
        timezone.localtime(timezone.now()).day) + '-' + str(timezone.localtime(timezone.now()).hour) + '/'

    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    print 'Going to saved searches...'

    save_searches = 'https://' + URL + '/vehicles#savedSearch'

    driver.get(save_searches)

    delay = 40  # seconds
    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'rover')))
        print "Saved Search Page is ready!"
    except TimeoutException:
        print "Loading took too much time!"
        # driver.save_screenshot('screenshot.png')
        driver.quit()

    print 'Going to click on our specific saved search...'

    driver.execute_script("$('.rover')[2].click()")

    delay = 40  # seconds
    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'vehicle-cost')))
        print "Resutls is ready!"
    except TimeoutException:
        print "Loading took too much time!"
        # driver.save_screenshot('screenshot.png')
        driver.quit()

    time.sleep(2)

    # StackOverFlow Example
    # select = Select(b.find_element_by_id('rs-page'))
    # print select.options
    # print [o.text for o in select.options]  # these are string-s
    # select.select_by_visible_text('100')

    # delay = 40  # seconds
    # try:
    #     WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'vehicle-cost')))
    #     print "Now each page has 100"
    # except TimeoutException:
    #     print "Loading took too much time!"

    page = 1
    while True:
        print get_driver_status()
        html_height = driver.execute_script("return $('body').height()")
        # print 'html_height', html_height

        # Scroll Down
        last_scrol_y = None
        count_same = 0
        while True:
            scroll_y = driver.execute_script("return $(window).height() + $('body').scrollTop()")
            if last_scrol_y == None or last_scrol_y != scroll_y:
                last_scrol_y = scroll_y
                count_same = 0
            else:
                count_same += 1

            # print 'Scroll Down.... scroll_y', scroll_y

            driver.execute_script("$('body').scrollTop($('body').scrollTop() + 300);")
            time.sleep(0.7)

            if count_same >= 3:
                print 'Read and Load result Page Completely'
                break

        html_source = driver.page_source

        f = open(new_dir + 'result' + str(page) + '.html', 'w')
        f.write(html_source.encode('utf-8'))
        f.close()

        page += 1

        time.sleep(3)

        isFinished = driver.execute_script("return $('.next').hasClass('disabled')")
        if isFinished == 'true' or isFinished == True:
            print 'Finish', type(isFinished)
            break

        print 'Click on Next'

        driver.find_element_by_css_selector('.next').click()

        delay = 40  # seconds
        try:
            WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'vehicle-cost')))
            print "Resutls is ready!"
        except TimeoutException:
            print "Loading took too much time!"
            # driver.save_screenshot('screenshot.png')
            driver.quit()

        time.sleep(15)


def parse_search_result():
    '''parse search result to retrieve list of cars'''

    new_dir = data_dir + folder_name + '/'
    onlyfiles = [f for f in listdir(new_dir) if isfile(join(new_dir, f))]

    all_car_info = []

    for result_file in onlyfiles:
        if not result_file.endswith('.html'):
            continue

        soup = BeautifulSoup(open(new_dir + result_file), 'html.parser')

        cars_elements = soup.select('.large-listing')

        car_info = []

        for i in range(len(cars_elements)):
            car_element = cars_elements[i]

            try:
                title_link = car_element.select('.vehicle-name')[0]
            except:
                print 'No Title for a car in ', result_file
                continue

            title = title_link.text
            car_id = title_link['href'].split('/')[2]

            VIN = car_element.select('.vehicle-desc > span')[0].text

            price_digit_elements = car_element.select(
                '.odometer-inside .odometer-digit .odometer-digit-inner .odometer-value')

            if price_digit_elements == 0:
                continue

            price = 0

            for price_digit_element in price_digit_elements:
                price *= 10
                price += int(price_digit_element.text)

            price = str(price)

            car_info.append({'car_id': car_id, 'vin': VIN, 'price': price, 'title': title})

        all_car_info.extend(car_info)

    return all_car_info


def fetch_vehicle_details(car_id):
    '''Fetch vehicle details page'''

    new_dir = data_dir + folder_name + '/' + 'car_details/'

    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    if exists(new_dir + 'car_' + str(car_id) + '.html'):
        print 'Fetched before'
        return

    fetch_vehicle_details_url = 'https://' + URL + '/vehicles#detail/' + str(car_id)
    driver.get(fetch_vehicle_details_url)

    delay = 40  # seconds
    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'vehicle-name')))
        print "Car Page Fetch Successfully"
    except TimeoutException:
        print "Loading took too much time!"
        # driver.save_screenshot('screenshot.png')
        driver.quit()

    html_height = driver.execute_script("return $('body').height()")
    # print 'html_height', html_height
    last_scrol_y = None
    count_same = 0
    while True:
        scroll_y = driver.execute_script("return $(window).height() + $('body').scrollTop()")
        if last_scrol_y == None or last_scrol_y != scroll_y:
            last_scrol_y = scroll_y
            count_same = 0
        else:
            count_same += 1
        # print 'Scroll Down.... scroll_y', scroll_y

        driver.execute_script("$('body').scrollTop($('body').scrollTop() + ($(window).height()/2));")
        time.sleep(0.5)

        html_height = driver.execute_script("return $('body').height()")
        # print 'html_height', html_height

        if count_same >= 3:
            print 'Read and Load Car Detail Page Completely'
            break

    html_source = driver.page_source

    f = open(new_dir + 'car_' + str(car_id) + '.html', 'w')
    f.write(html_source.encode('utf-8'))
    f.close()

    driver.execute_script("$('body').scrollTop(0);")

    # Fetch Carfax
    driver.execute_script("window.location.href = ko.dataFor($('img[alt=Carfax]').parent().get(0)).linkToCarFax()");

    carfax_fetched = True

    delay = 40  # seconds
    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'fs_0')))
        print "Carfax step 1!"
    except TimeoutException:
        print "Loading took too much time!"
        # driver.save_screenshot('screenshot.png')
        carfax_fetched = False

    if carfax_fetched == True:
        driver.execute_script("jQuery('#fs_0').click();")
        delay = 10  # seconds // TODO: SHAYAN!! CHANGE TO 40
        try:
            WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'results')))
            print "Carfax step 2!"
        except TimeoutException:
            print "Loading took too much time!"
            # driver.save_screenshot('screenshot.png')
            carfax_fetched = False

    if carfax_fetched == True:
        carfax_html_source = driver.page_source

        f = open(new_dir + 'car_carfax_' + str(car_id) + '.html', 'w')
        f.write(carfax_html_source.encode('utf-8'))
        f.close()

    wait_about(30, 30)


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


def get_car_lists_for_different_actions(all_car_info, do_remove=False):
    should_fetch = []
    should_remove = []
    should_update_price = []

    cars = Car.objects.filter(bg_car_id__isnull=False, available_on_bg=True,
                              is_it_available=True)

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
            old_update = False
            same_old_car = Car.objects.filter(bg_car_id__isnull=False, is_it_available=False,
                                              vin=car_info['vin'])
            if same_old_car.count() == 1:
                same_old_car = same_old_car.first()
                if car_info['price'] != None and same_old_car.original_price != None and abs(
                                same_old_car.original_price - int(car_info['price'])) <= 700 and exists(
                    same_old_car.cardetail.detail_html):
                    update_count += 1
                    should_update_price.append(car_info)
                    old_update = True

            if old_update == False:
                new_count += 1
                should_fetch.append(car_info)

    print 'remove', remove_count, 'cars'
    print 'should update', update_count, 'cars'
    print 'should add', new_count, 'cars'
    print 'repetitive ', rep, 'cars'
    return should_fetch, should_remove, should_update_price


def get_mini_model_and_trim(title):
    models = CarModel.objects.filter(make__name__iexact='MINI')

    my_model = None
    my_trim = None

    found = False
    for model in models:
        if model.name.lower() in title.lower():
            found = True
            if my_model == None or len(model.name) > len(my_model.name):
                my_model = model

    if my_model != None:
        trims = CarTrim.objects.filter(model__name__iexact=my_model.name)

        found = False
        for trim in trims:
            if trim.name.lower() in title.lower():
                found = True
                my_trim = trim
                break

    return my_model, my_trim


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
    should_fetch, should_remove, should_update_price = get_car_lists_for_different_actions(all_car_info)

    if len(should_fetch) > 0:
        # login()
        for i in range(len(should_fetch)):
            try:
                fetch_vehicle_details(should_fetch[i]['car_id'])
            except:
                print 'Error occured in fetch_vehicle_details of bg car ', should_fetch[i]['car_id']

    return should_remove, should_update_price


def update_db_process(should_remove, should_update_price):
    new_dir = data_dir + folder_name + '/' + 'car_details/'

    shoud_fetch_again = []

    print '=====> Remove not available cars (bg)'

    for car_vin in should_remove:
        car = Car.objects.get(vin=car_vin)
        car.available_on_bg = False
        car.bg_removed_at = timezone.localtime(timezone.now())

        if car.available_on_mo == False and car.available_on_bg == False and car.available_on_ove == False and car.available_on_ade == False:
            car.is_it_available = False

        car.save()
        print 'Remove ', car_vin

    print '=====> End Removing'

    print '=====> Update Car Prices'

    for car_info in should_update_price:
        car = Car.objects.get(vin=car_info['vin'])
        last_price = car.original_price
        car.original_price = car_info['price']
        car.available_on_bg = True
        car.is_it_available = True
        car.save()
        print 'Update ', car_info['car_id'], 'Price ', last_price, '-->', car_info['price']

    print '=====> End Updating Prices'

    if not os.path.exists(new_dir):
        return

    onlyfiles = [f for f in listdir(new_dir) if isfile(join(new_dir, f))]

    for car_detail_file in onlyfiles:
        if not car_detail_file.endswith('.html'):
            continue
        if car_detail_file.startswith('car_carfax'):
            continue

        car_id = car_detail_file.split('.')[0].split('_')[1]  # Retrive car id from file name
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
        except:
            print 'Error Occured in parsing car page'
            continue

        if car_info == None:
            print 'should fetch again ------> ', car_id
            shoud_fetch_again.append(car_id)
            continue
        print 'Reading car page is finished'

        carfax = None
        if carfax_exist == True:
            print 'Start reading car carfax'
            try:
                car_carfax_info = parse_carfax(carfax_path)
                carfax = get_carfax_object(car_carfax_info)  # carfax object without car set
            except:
                print 'Error Occured in parsing carfax'
                # continue
            print 'reading car carfax is finished'

        try:
            car = Car.objects.get(vin=car_info['vin'])
            car.last_updated_time = timezone.localtime(timezone.now())
            car.is_rejected = False
            car.eligible_to_display = False
            print 'UPDATIIIIIIIIIIIIIIIIIIIIIIIIIIIIING CAR'
        except:
            print 'NEWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW CAR'
            car = Car()

        car.available_on_bg = True
        car.is_it_available = True
        car.vin = car_info['vin']
        car.bg_car_id = car_id
        car.car_model = car_info['title']

        if car_info['make'] == 'MINI':
            my_model, my_trim = get_mini_model_and_trim(car_info['title'])
            car.model = my_model
            car.trim = my_trim
        elif car_info['make'] == 'BMW':
            my_model, my_trim = get_bmw_model_and_trim(car_info['title'])
            car.model = my_model
            car.trim = my_trim

        car.last_checking = timezone.localtime(timezone.now())
        car.original_price = car_info['price']
        car.year = int(car_info['year'])
        car.grade = float(car_info['AutoGrade'])

        # Location
        try:
            location_name = ' '.join(car_info['Vehicle Location'].split())
            location = Location.objects.get(name__iexact=location_name)
            car.location = location
        except:
            print 'Location is not in database -------->' + car_info['Vehicle Location']
            # pass

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
        car_detail.vehicle_options = '\n'.join(car_info['options'])
        car_detail.miles = car_info['Odometer'].replace(',', '')
        car_detail.exterior = car_info.get('Exterior Color')
        car_detail.interior = car_info.get('Interior Color')
        car_detail.engine = car_info.get('Engine Type')

        car_detail.odor = car_info.get('Odor')
        car_detail.msrp = car_info['MSRP'][1:].replace(',', '')
        car_detail.announcements = car_info.get('Announced Conditions')
        # car_detail.value_added_options = car_info['value added options']
        # car_detail.drive = car_info['drive']
        # car_detail.keys = car_info[''],
        #
        # # It should not be DATE
        # if len(car_info['warranty date']) > 0:
        #     date_set = car_info['warranty date'].split('-')
        #     warranty_date = '20' + date_set[2] + '-' + date_set[0] + '-' + date_set[1]
        #     car_detail.warranty_date = warranty_date

        car_detail.save()

        # Repairs
        if 'repairs' in car_info:
            repairs = Repair.objects.filter(car=car)
            repairs.delete()

            for ans_item in car_info['repairs']:
                repair = Repair(car=car)
                repair.repaired = ans_item[1]
                repair.condition = ans_item[0]
                repair.severity = ans_item[2]
                repair.repair_type = None
                repair.save()

        # Damages
        if 'damages' in car_info:
            damages = Damage.objects.filter(car=car)
            damages.delete()

            for ans_item in car_info['damages']:
                damage = Damage(car=car)
                damage.part = ans_item[1]
                damage.condition = ans_item[0]
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

        # Tires
        if 'tires' in car_info:
            tires = Tire.objects.filter(car=car)
            tires.delete()

            for t in car_info['tires']:
                tire = Tire(car=car)
                tire.type = t[0]
                tire.tread = t[1]
                tire.brand = t[2]
                tire.size = t[3]
                tire.save()

    print 'should fetch agains', shoud_fetch_again


class Command(BaseCommand):
    help = 'Crawl ' + URL

    def add_arguments(self, parser):
        parser.add_argument('type', type=str)

    def change_crawler_status(self, status):
        self.bg_crawler.status = status
        if status == "RUNNING":
            self.bg_crawler.last_run = timezone.now()
        self.bg_crawler.save()

    def handle(self, *args, **options):
        global folder_name, driver

        self.bg_crawler = Crawler.objects.get(name="bg")

        try:
            if options['type'] == 'all':
                self.change_crawler_status("RUNNING")
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)

                # Start Process

                print "-------> bg"

                driver = webdriver.PhantomJS('/usr/local/bin/phantomjs')
                driver.implicitly_wait(10)  # wait 10 seconds when doing a find_element before carrying on
                driver.set_window_size(1920, 1080)

                # Search
                print "===================== Start Search Process ====================="
                search_process()
                print "===================== End Search Process ====================="

                folder_name = get_latest_search_folder_name()
                print folder_name

                # Analyze results and fetch car details
                print "===================== Start Fetch Cars Process ====================="
                should_remove, should_update_price = fetch_cars_process()
                print "===================== End Fetch Cars Process ====================="

                driver.quit()

                # Update DB
                print "===================== Start Update DB Process ====================="
                update_db_process(should_remove, should_update_price)
                print "===================== End Update DB Process ====================="

                # Calculate Prices
                print "===================== Start Calculate Final Prices Process ====================="
                call_command('calculate_final_prices', 'bg_cars')
                print "===================== End Calculate Final Prices Process ====================="

            elif options['type'] == 'fetch':
                self.change_crawler_status("RUNNING")
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)

                # Start Process

                print "-------> bg"

                driver = webdriver.PhantomJS('/usr/local/bin/phantomjs')
                driver.implicitly_wait(10)  # wait 10 seconds when doing a find_element before carrying on
                driver.set_window_size(1920, 1080)

                # Search
                print "===================== Start Search Process ====================="
                search_process()
                print "===================== End Search Process ====================="

                folder_name = get_latest_search_folder_name()
                print folder_name

                # Analyze results and fetch car details
                print "===================== Start Fetch Cars Process ====================="
                should_remove, should_update_price = fetch_cars_process()
                print "===================== End Fetch Cars Process ====================="

                driver.quit()

            elif options['type'] == 'load':
                self.change_crawler_status("RUNNING")
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)

                # Start Process

                print "-------> bg"

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
                call_command('calculate_final_prices', 'bg_cars')
                print "===================== End Calculate Final Prices Process ====================="
        finally:
            self.change_crawler_status("IDLE")
