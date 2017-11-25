# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand
from django.core.management import call_command

import os, sys
import httplib
import socket
import traceback

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver import remote
from selenium.common.exceptions import NoSuchElementException

from os import listdir
from os.path import isfile, join, exists

from crawler.management.common import *
from crawler.models import *

from administrator.tasks import ade_all

from django.conf import settings

from django.template import Context
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives

from datetime import datetime, timedelta

data_dir = 'crawler/management/data/ade/'

driver = None

unknown_locations = set()
unknown_makes = set()
unknown_models = set()

delay = 30  # seconds

URL = os.environ.get('ADE_URL', '')

ade_make_dict = {'MERCEDES': 'Mercedes benz', 'Mercedes': 'Mercedes benz'}
ade_location_dict = {'LAS VEGAS, NV': 'Adesa Las Vegas', 'SEATTLE, WA': 'Seattle Washington',
                     'SOUTH SAN FRANC...': 'South San Francisco, CA',
                     'SAN LUIS OBISPO...': 'San Luis Obispo, CA',
                     'LOS ANGELES, CA': 'Adesa Los Angeles', 'PORTLAND, OR': 'Portland Oregon',
                     'SALT LAKE CITY, UT': 'Salt lake City, Utah', 'DENVER, CO': 'Manheim Denver',
                     'RANCHO SANTA MA...': 'Rancho Santa Margarita', 'NORTH HOLLYWOOD...': 'Hollywood, CA',
                     'ADESA SAN DIEGO': 'San Diego, CA', 'RIVERSIDE, CA': 'Manheim Riverside',
                     'CITY OF INDUSTR...': 'City of industry, CA', 'SAN JUAN CAPIST...': 'San Juan Capistrano, CA',
                     'HUNTINGTON BEAC...': 'Huntington Beach, CA', 'APACHE JUNCTION...': 'Apache Junction, AZ',
                     'NORTH HILLS,, CA': 'NORTH HILLS, CA', 'LAKE HAVASU CIT...': 'Lake Havasu City, AZ',
                     'WEST VALLEY CIT...': 'West Valley City, UT'
                     }

sent_emails = set()

allowed_saved_searches = ['BMW Financial Services', 'shayan', 'Shayan Acura', 'Shayan Audi', 'Shayan Benz',
                          'Shayan Cadillac', 'Shayan Chevrolet',
                          'Shayan Chrysler', 'Shayan Dodge', 'Shayan Fiat', 'Shayan Ford', 'Shayan GMC', 'Shayan Honda',
                          'Shayan Hyundai', 'Shayan Infiniti', 'Shayan Kia', 'Shayan Nissan',
                          'Shayan Toyota']

historical_eligible_saved_searches = ['BMW Financial Services']


class Command(BaseCommand):
    help = 'Crawl ' + URL

    def add_arguments(self, parser):
        parser.add_argument('type', type=str)

        # Named (optional) argument
        parser.add_argument(
            '-saved_search_names',
            nargs='+',
            action='store',
            dest='saved_search_names',
            default=True,
            help='List of saved search names',
        )

        # Named (optional) argument
        parser.add_argument(
            '-nofirstsearch',
            action='store_true',
            dest='nofirstsearch',
            default=False,
            help='No First Search of Saved Searches',
        )

        # Named (optional) argument
        parser.add_argument(
            '-withremove',
            action='store_true',
            dest='withremove',
            default=False,
            help='Remove cars',
        )

        # Named (optional) argument
        parser.add_argument(
            '-until',
            action='store',
            dest='until',
            default=False,
            help='Keep current search results unitl',
        )

    def change_crawler_status(self, status):
        self.ade_crawler.status = status
        if status == "RUNNING":
            self.ade_crawler.last_run = timezone.now()
        self.ade_crawler.save()

    def handle(self, *args, **options):

        self.ade_crawler = Crawler.objects.get(name="ade")

        # Search New Cars, Fetch them (Phase 1), Analyze them, Update Database (Phase 2)
        if options['type'] == 'all':
            if self.ade_crawler.status == "IDLE":
                try:
                    self.change_crawler_status("RUNNING")
                    prepare_crawling(options['saved_search_names'])
                    search_and_process_phase(options['saved_search_names'], True, options['nofirstsearch'])
                    if options['withremove']:
                        remove_and_update_db()
                    search_and_process_phase(options['saved_search_names'], False, True)
                    add_to_db_and_calculate_new_price_phase()
                finally:
                    self.change_crawler_status("IDLE")
            else:
                print "Previous Ade is still running"
        elif options['type'] == 'keep':
            try:
                self.change_crawler_status("RUNNING")
                prepare_crawling(options['saved_search_names'])
                search_and_process_phase(options['saved_search_names'], True, options['nofirstsearch'])
                search_and_process_phase(options['saved_search_names'], False, True)
                add_to_db_and_calculate_new_price_phase()
                keep_until_sale_date()
            finally:
                self.change_crawler_status("IDLE")

        elif options['type'] == 'remove':
            try:
                self.change_crawler_status("RUNNING")
                prepare_crawling(options['saved_search_names'])
                search_and_process_phase(options['saved_search_names'], True, options['nofirstsearch'])
                remove_and_update_db()
            finally:
                self.change_crawler_status("IDLE")

        # Only Search New Cars and Fetch Them (Phase 1)
        elif options['type'] == 'fetch':
            try:
                self.change_crawler_status("RUNNING")
                prepare_crawling(options['saved_search_names'])
                search_and_process_phase(options['saved_search_names'], False, options['nofirstsearch'])
            finally:
                self.change_crawler_status("IDLE")

        # Only Analyze Fetched Data and Update Database (Phase 2)
        elif options['type'] == 'load':
            prepare_crawling(options['saved_search_names'])
            add_to_db_and_calculate_new_price_phase()

        elif options['type'] == 'reload':
            cars = Car.objects.filter(ade_car_id__isnull=False)
            for car in cars:
                print car.id, ": ", car.cardetail.detail_html
                if exists(car.cardetail.detail_html):
                    car_path = car.cardetail.detail_html
                    filename = car_path.split('/')[-1]
                    folder_path = '/'.join(car_path.split('/')[0:-1]) + '/'
                    parse_file_update_db(filename, folder_path, True)
                else:
                    print >> sys.stderr, 'html file does not exist. car: ', car.id, 'html: ' + car.cardetail.detail_html

            # Calculate Prices
            print "===================== Start Calculate Final Prices Process ====================="
            call_command('calculate_final_prices', 'ade_cars')
            print "===================== End Calculate Final Prices Process ====================="

        elif options['type'] == 'reload_current':
            cars = Car.objects.available_cars().filter(ade_car_id__isnull=False)
            for car in cars:
                print car.id, ": ", car.cardetail.detail_html
                if exists(car.cardetail.detail_html):
                    car_path = car.cardetail.detail_html
                    filename = car_path.split('/')[-1]
                    folder_path = '/'.join(car_path.split('/')[0:-1]) + '/'
                    parse_file_update_db(filename, folder_path, True)
                else:
                    print >> sys.stderr, 'html file does not exist. car: ', car.id, 'html: ' + car.cardetail.detail_html

            # Calculate Prices
            print "===================== Start Calculate Final Prices Process ====================="
            call_command('calculate_final_prices', 'ade_cars')
            print "===================== End Calculate Final Prices Process ====================="

        elif options['type'] == 'remove_empty_detail_files':
            remove_empty_detail_files()

        elif options['type'] == 'remove_without_carfax':
            remove_without_carfax()


##########################################################################################

def prepare_crawling(saved_search_names):
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    print "-------> ade"
    print "Saved Search Names: ", saved_search_names


def search_and_process_phase(saved_search_names, onlyremove, nofirstsearch):
    global folder_name, driver

    driver = webdriver.PhantomJS('/usr/local/bin/phantomjs')

    if saved_search_names == True:
        saved_search_names = allowed_saved_searches
    else:
        # Check list to be allowed
        for saved_search_name in saved_search_names:
            if not saved_search_name in allowed_saved_searches:
                print "This saved search is not in the allowed list:", saved_search_name
                exit()

    # Login
    print "===================== Start Login ====================="
    login()
    print "===================== End Login ====================="

    if nofirstsearch == False:
        # Search
        print "===================== Start Search Process ====================="
        search_process(saved_search_names)
        print "===================== End Search Process ====================="

    folder_name = get_latest_search_folder_name()
    print folder_name

    if not onlyremove:
        # Process Search Results and Fetch Missing Cars Details
        print "===================== Start Fetch Cars Process ====================="
        fetch_cars_process()
        print "===================== End Fetch Cars Process ====================="

    driver.quit()  # Done with Browser


def remove_and_update_db():
    all_car_info = parse_search_result()
    action_list = get_car_lists_for_different_actions(all_car_info)

    # Remove and Update Database
    print "===================== Start Update DB Process ====================="
    update_db_process(action_list)
    print "===================== End Update DB Process ====================="


def add_to_db_and_calculate_new_price_phase():
    global folder_name

    folder_name = get_latest_search_folder_name()
    print folder_name

    # Add to Database
    print "===================== Start Update DB Process ====================="
    add_to_db_process()
    print "===================== End Update DB Process ====================="

    # Calculate Prices
    print "===================== Start Calculate Final Prices Process ====================="
    call_command('calculate_final_prices', 'ade_cars')
    print "===================== End Calculate Final Prices Process ====================="


def keep_until_sale_date():
    all_car_info = parse_search_result()

    for car_info in all_car_info:
        if not Car.objects.filter(vin=car_info['VIN']).exists():
            print car_info['VIN'] + " with sale date is not available in database"
            continue

        if car_info['saleDate'] != None:
            car = Car.objects.get(vin=car_info['VIN'])
            car.ade_car_id = car_info['car_id']
            car.available_on_ade = True
            car.is_it_available = True
            try:
                car.remain_until = datetime.strptime(car_info['saleDate'] + '-23:59', '%m/%d/%y-%H:%M') - timedelta(
                    days=1)
                car.save()
                print "Added Sale Date to : " + car_info['VIN']
            except:
                print "Sale Date format not as expected: " + car_info['saleDate']


##########################################################################################

def search_process(saved_search_names):
    new_time_directory = data_dir + str(timezone.localtime(timezone.now()).year) + '-' + str(
        timezone.localtime(timezone.now()).month) + '-' + str(
        timezone.localtime(timezone.now()).day) + '-' + str(timezone.localtime(timezone.now()).hour) + '/'

    if not os.path.exists(new_time_directory):
        os.makedirs(new_time_directory)

    # Remove previous files
    if exists(new_time_directory):
        for name in os.listdir(new_time_directory):
            if os.path.isfile(os.path.join(new_time_directory, name)) and name.startswith('result'):
                os.remove(os.path.join(new_time_directory, name))

    i = 0
    failed = False
    while i < len(saved_search_names):
        saved_search = saved_search_names[i]
        b = fetch_search_results(saved_search, failed, new_time_directory)
        if b == True:
            failed = False
            i += 1
        else:
            failed = True


def login():
    driver.get("https://" + URL + "/home")
    username_elem = driver.find_element_by_id('adesaUserName')
    password_elem = driver.find_element_by_name('password')

    username_elem.clear()
    username_elem.send_keys(os.environ.get('ADE_USERNAME', ''))

    password_elem.clear()
    password_elem.send_keys(os.environ.get('ADE_PASSWORD', ''))

    driver.find_element_by_css_selector('.btn-login').click()

    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'searchSubmit_vehicles')))
        print "Login Successfully"
    except KeyboardInterrupt:
        sys.exit()
    except TimeoutException:
        print >> sys.stderr, "Login Failed!"
        send_email_to_technical_administrator('ade Login Failed!')
        sys.exit()


def logout():
    driver.get('https://buy.' + URL + '/openauction/logout.html')

    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'accountName_temp')))
        print "Logout Successfully"
    except KeyboardInterrupt:
        sys.exit()
    except TimeoutException:
        print >> sys.stderr, "Logout Failed!"
        send_email_to_technical_administrator('ade Logout Failed!')
        sys.exit()


##########################################################################################

def fetch_search_results(saved_search_name, failed, new_time_directory):
    time_string = str(timezone.localtime(timezone.now()).year) + '-' \
                  + str(timezone.localtime(timezone.now()).month) + '-' \
                  + str(timezone.localtime(timezone.now()).day) \
                  + '-' + str(timezone.localtime(timezone.now()).hour) + '/'
    saved_searches_page = 'https://buy.' + URL + '/openauction/savedsearches4.html'

    parent_search_dir = os.path.join(new_time_directory, "search")
    if not os.path.exists(parent_search_dir):
        os.makedirs(parent_search_dir)

    saved_search_folder_name = os.path.join(parent_search_dir, saved_search_name)
    if not os.path.exists(saved_search_folder_name):
        os.makedirs(saved_search_folder_name)

    driver.get(saved_searches_page)
    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'savedSearchTable')))
        print "Saved Search Page is ready! Gonna Click On '" + saved_search_name + "'"
    except KeyboardInterrupt:
        sys.exit()
    except TimeoutException:
        if failed == False:
            driver.save_screenshot(
                'crawlers_screenshot/' + time_string + '_ade_savedsearch_page1_' + saved_search_name + '.png')
            print >> sys.stderr, "Loading Saved Search Page took too much time!"

    wait_about(3)

    if failed == True:
        driver.execute_script("jQuery('body').scrollTop(0)")

    found = False
    is_empty = False
    saved_search_rows = driver.find_elements_by_css_selector('#savedSearchTable tr')
    for saved_search_row in saved_search_rows:
        if saved_search_row.text.split(' (')[0] == saved_search_name:
            try:
                if int(saved_search_row.find_element_by_css_selector('.numberOfVehicles').text) == 0:
                    is_empty = True
                    break
            except:
                print 'Non Integer: ' + saved_search_row.find_element_by_css_selector('.numberOfVehicles').text

            search_button = saved_search_row.find_element_by_css_selector('#searchButton')
            edit_button = saved_search_row.find_element_by_css_selector('#editButton')
            driver.execute_script(
                "jQuery('body').scrollTop(" + str(int(search_button.get_attribute('offsetTop')) + 300) + ");")
            wait_about(2, 0)
            # search_button.click()
            edit_button.click()
            found = True
            break

    if is_empty == True:
        print saved_search_name + ' has ZERO cars. So do not open it'
        return True

    if found == False:
        print >> sys.stderr, "ade Not found saved search: " + saved_search_name
        driver.save_screenshot('crawlers_screenshot/' + time_string + '_ade_saved_search_NOT_FOUND_' + '_'.join(
            saved_search_name.split()) + '.png')
        if not 'not_found_saved_search' in sent_emails:
            send_email_to_technical_administrator(
                "ade Not found saved search: " + saved_search_name + ' ' + str(saved_search_rows))
            sent_emails.add('not_found_saved_search')
        return False

    # try:
    #     WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'resultCaption')))
    #     print "Search Result is ready!"
    # except KeyboardInterrupt:
    #     sys.exit()
    # except TimeoutException:
    #     driver.save_screenshot('crawlers_screenshot/' + time_string + '_ade_search_result_page_' + '_'.join(saved_search_name.split()) + '.png')
    #     print >> sys.stderr, "Loading Search Result page took too much time!"
    #     if not 'not_load_saved_search' in sent_emails:
    #         send_email_to_technical_administrator("ade does not load saved search: " + saved_search_name)
    #         sent_emails.add('not_load_saved_search')
    #
    #     return False

    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'breadcrumb_mk')))
        print "Edit Page is ready!"
    except KeyboardInterrupt:
        sys.exit()
    except TimeoutException:
        driver.save_screenshot('crawlers_screenshot/' + time_string + '_ade_search_edit_page_' + '_'.join(
            saved_search_name.split()) + '.png')
        print >> sys.stderr, "Loading Search Result page took too much time!"
        if not 'not_load_saved_search' in sent_emails:
            send_email_to_technical_administrator("ade does not load saved search: " + saved_search_name)
            sent_emails.add('not_load_saved_search')

        return False

    search_button_in_edit = driver.find_element_by_css_selector('#searchSubmit')
    search_button_in_edit.click()

    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'resultCaption')))
        print "Search Result is ready!"
    except KeyboardInterrupt:
        sys.exit()
    except TimeoutException:
        driver.save_screenshot('crawlers_screenshot/' + time_string + '_ade_search_result_page_' + '_'.join(
            saved_search_name.split()) + '.png')
        print >> sys.stderr, "Loading Search Result page took too much time!"
        if not 'not_load_saved_search' in sent_emails:
            send_email_to_technical_administrator("ade does not load saved search: " + saved_search_name)
            sent_emails.add('not_load_saved_search')

        return False

    file_count = len([name for name in os.listdir(saved_search_folder_name) if
                      (os.path.isfile(os.path.join(saved_search_folder_name, name)) and name.startswith('result'))])

    page = file_count + 1
    html_source = driver.page_source

    f = open(os.path.join(saved_search_folder_name, 'result' + str(page) + '.html'), 'w')
    f.write(html_source.encode('utf-8'))
    f.close()

    page += 1
    while True:
        r = driver.find_elements_by_css_selector('.pagenumber span:last-child a')
        if len(r) == 0 or r[0].text != '>':
            page -= 1
            break
        else:
            r[0].click()
            wait_about(20)  # wait for page to load completely

            print "Load Next Page!"
            html_source = driver.page_source

            f = open(os.path.join(saved_search_folder_name, 'result' + str(page) + '.html'), 'w')
            f.write(html_source.encode('utf-8'))
            f.close()

            page += 1

    return True


##########################################################################################

def fetch_cars_process():
    # Analyze results and fetch car details
    all_car_info = parse_search_result()
    action_list = get_car_lists_for_different_actions(all_car_info)
    loginlogout_times = []
    i = 30
    while i < len(action_list['fetch']):
        rand = int(random.random() * 9) - 4
        newI = i + rand
        if newI > 0 and newI < len(action_list['fetch']):
            loginlogout_times.append(newI)
        i += 30

    if len(action_list['fetch']) > 0:
        c = 0
        for i in range(len(action_list['fetch'])):
            # Login and Logout to prevent session flag
            if c in loginlogout_times:
                logout()
                wait_about(25, 20)
                login()

            try:
                b = fetch_vehicle_details(action_list['fetch'][i]['car_id'])
                if b == True:
                    c += 1
            except KeyboardInterrupt:
                sys.exit()
            except:
                car_path = data_dir + folder_name + '/' + 'car_details/' + 'car_' + str(
                    action_list['fetch'][i]['car_id']) + '.html'
                if os.path.exists(car_path):
                    os.remove(car_path)
                    print "removed " + car_path
                print >> sys.stderr, 'Error occured in fetch_vehicle_details of ade car ', action_list['fetch'][i][
                    'car_id']
                traceback.print_exc()
                print "==========================="


def parse_search_result():
    '''Parse search result to retrieve list of cars'''

    new_dir = os.path.join(data_dir, folder_name)
    parent_search_dir = os.path.join(new_dir, "search")
    search_folders_list = [f for f in listdir(parent_search_dir) if not os.path.isfile(f)]

    all_car_info = []

    for saved_search_folder_name in search_folders_list:
        saved_search_folder_path = os.path.join(parent_search_dir, saved_search_folder_name)

        result_file_list = [f for f in listdir(saved_search_folder_path)]
        for result_file in result_file_list:
            if not result_file.endswith('.html'):
                continue

            soup = BeautifulSoup(open(os.path.join(saved_search_folder_path, result_file)), 'html.parser')

            cars_elements = soup.select('.listing-block')

            car_info = []

            for i in range(len(cars_elements)):
                car_element = cars_elements[i]
                title_link = car_element.select('.srp-content .title .srp-model a')[0]

                title = title_link.text
                car_id = title_link['href'].split('&')[0].split('=')[1]

                VIN = car_element.select('.srp-content .title .srp-model .titleVin')[0].text[2:]
                grade_elements = car_element.select('.srp-content .grade')
                grade = None
                if len(grade_elements) == 1:
                    grade = float(car_element.select('.srp-content .grade')[0].contents[2].strip())
                    # if grade < 2:  # ade GRADE RESTRICTION. TODO: make it parameter
                    #     continue

                price = None

                price_elements = car_element.select('.srp-content .start_price')
                if len(price_elements) == 0:
                    # Do not have BID NOW

                    price_elements = car_element.select('.srp-content .buy_price')
                    if len(price_elements) == 0:
                        # Do not have BUY NOW
                        # print VIN
                        # if keep == False:
                        #     continue
                        pass
                    else:
                        price_elements = price_elements[0].contents

                        if len(price_elements) > 1:
                            price = price_elements[1].strip().split('$')[1].replace(',', '')
                else:
                    price_elements = price_elements[0].contents

                    if len(price_elements) > 1:
                        price = price_elements[1].strip().split('$')[1].replace(',', '').split(' ')[0]

                saleDate = None
                sale_date_elements = car_element.select('.liveblock_scheduled_sale_date')
                if len(sale_date_elements) > 0:
                    sale_date_element = sale_date_elements[0].contents
                    saleDate = sale_date_element[1]

                car_info.append(
                    {'car_id': car_id, 'VIN': VIN, 'price': price, 'grade': grade, 'title': title, 'saleDate': saleDate,
                     'saved_search_name': saved_search_folder_name})

            all_car_info.extend(car_info)

    return all_car_info


def get_car_lists_for_different_actions(all_car_info):
    action_list = {}
    action_list['fetch'] = []
    action_list['remove'] = []
    action_list['update_price'] = []
    action_list['use_historical_information'] = []

    cars = Car.objects.filter(ade_car_id__isnull=False, available_on_ade=True, is_it_available=True)

    remove_count = 0
    update_count = 0
    new_count = 0
    historical_count = 0
    repetitive = 0

    # TODO: do it in log(n), not n^2
    for car in cars:
        find = False
        for car_info in all_car_info:
            if car_info['VIN'] == str(car.vin):
                if car_info['price'] != None and str(car_info['price']) != str(car.original_price):
                    # Price has been changed. Should get updated
                    if car.original_price != None and abs(
                                    car.original_price - int(car_info['price'])) <= 700:
                        print str(car.original_price), '------->', car_info['price'], '(Update)'
                        update_count += 1
                        action_list['update_price'].append(car_info)
                    else:
                        print str(car.original_price), '------->', car_info['price'], '(Fetch)'
                        new_count += 1
                        action_list['fetch'].append(car_info)
                else:
                    repetitive += 1
                find = True
                break

        if find == False:
            remove_count += 1
            action_list['remove'].append(car.vin)

    for car_info in all_car_info:
        find = False
        for car in cars:
            if car_info['VIN'] == str(car.vin):
                find = True
                break

        if find == False:
            old_update = False
            same_old_car = Car.objects.filter(ade_car_id__isnull=False, is_it_available=False, vin=car_info['VIN'])
            if same_old_car.count() == 1:
                same_old_car = same_old_car.first()

                if car_info['price'] == None and same_old_car.original_price != None and car_info[
                    'saleDate'] != None and car_info['saved_search_name'] in historical_eligible_saved_searches:
                    historical_count += 1
                    action_list['use_historical_information'].append(car_info)
                    old_update = True
                elif car_info['price'] != None and same_old_car.original_price != None and abs(
                                same_old_car.original_price - int(car_info['price'])) <= 700:
                    update_count += 1
                    action_list['update_price'].append(car_info)
                    old_update = True

            if old_update == False:
                new_count += 1
                action_list['fetch'].append(car_info)

    print 'remove', remove_count, 'cars'
    print 'should update', update_count, 'cars'
    print 'should fetch', new_count, 'cars'
    print 'should use historical version', historical_count, 'cars'
    print 'repetitive ', repetitive, 'cars'

    return action_list


def fetch_vehicle_details(car_id):
    '''Fetch vehicle details page'''

    new_dir = os.path.join(data_dir, folder_name, 'car_details')

    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    if exists(os.path.join(new_dir, 'car_' + str(car_id) + '.html')):
        print 'Fetched before'
        return False

    fetch_vehicle_details_url = 'https://buy.' + URL + '/openauction/detail.html?vehicleId=' + str(car_id)
    driver.get(fetch_vehicle_details_url)

    delay = 10  # seconds
    try:
        print 'Waiting'
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'adesaDamages')))
        print "Car Page Fetch Successfully"
    except KeyboardInterrupt:
        sys.exit()
    except TimeoutException:
        driver.save_screenshot('crawlers_screenshot/' + folder_name + '_ade_car_page_' + str(car_id) + '.png')
        print "Loading took too much time!"

    html_source = driver.page_source
    f = open(os.path.join(new_dir, 'car_' + str(car_id) + '.html'), 'w')
    f.write(html_source.encode('utf-8'))
    f.close()

    print 'url: ' + fetch_vehicle_details_url
    print "saved in " + new_dir + 'car_' + str(car_id) + '.html'

    # Fetch Carfax
    carfax_fetched = True

    try:
        driver.execute_script("jQuery('#CarfaxLink').removeAttr('target');")
        carfax_elem = driver.find_element_by_id('CarfaxLink')

        # driver.execute_script(
        #     "jQuery('body').scrollTop(" + str(int(carfax_elem.get_attribute('offsetTop')) + 300) + ");")
        #
        # wait_about(1, 0)
        carfax_elem.click()

        delay = 60  # seconds
        try:
            WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#fs_0, #results")))
            print "Carfax step 1!"
        except KeyboardInterrupt:
            sys.exit()
        except TimeoutException:
            carfax_fetched = False
            driver.save_screenshot('crawlers_screenshot/' + folder_name + '_ade_carfax1_' + str(car_id) + '.png')
            print "Loading took too much time!"
    except KeyboardInterrupt:
        sys.exit()
    except:
        carfax_fetched = False

    if carfax_fetched == True:

        carfax_loaded_directly = True
        try:
            driver.find_element_by_id('results')
        except NoSuchElementException:
            carfax_loaded_directly = False

        if not carfax_loaded_directly:
            driver.execute_script("jQuery('#fs_0').click();")
            delay = 60
            try:
                WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'results')))
                print "Carfax step 2!"
            except KeyboardInterrupt:
                sys.exit()
            except TimeoutException:
                driver.save_screenshot('crawlers_screenshot/' + folder_name + '_ade_carfax2_' + str(car_id) + '.png')
                carfax_fetched = False
                print "Loading took too much time!"

    if carfax_fetched == True:
        carfax_html_source = driver.page_source

        f = open(os.path.join(new_dir, 'car_carfax_' + str(car_id) + '.html'), 'w')
        f.write(carfax_html_source.encode('utf-8'))
        f.close()

    wait_about(30, 70)
    return True


##########################################################################################

def update_db_process(action_list):
    print '=====> Remove not available cars (ade)'

    for car_vin in action_list['remove']:
        car = Car.objects.get(vin=car_vin)
        car.available_on_ade = False
        car.ade_removed_at = timezone.localtime(timezone.now())

        if car.available_on_mo == False and car.available_on_bg == False and car.available_on_ove == False and car.available_on_ade == False:
            car.is_it_available = False

        car.save()
        print 'Remove ', car_vin

    print '=====> End Removing'

    print '=====> Update Car Prices'

    print action_list['update_price']
    for car_info in action_list['update_price']:
        car = Car.objects.get(vin=car_info['VIN'])
        last_price = car.original_price
        car.original_price = car_info['price']
        car.ade_car_id = car_info['car_id']
        car.available_on_ade = True
        car.is_it_available = True
        car.save()
        print 'Update ', car_info['car_id'], 'Price ', last_price, '-->', car_info['price']

    print '=====> End Updating Prices'

    print '=====> Use Historical Cars'

    print action_list['use_historical_information']
    for car_info in action_list['use_historical_information']:
        car = Car.objects.get(vin=car_info['VIN'])
        car.ade_car_id = car_info['car_id']
        car.available_on_ade = True
        car.is_it_available = True
        car.save()
        print 'Make ', car_info['car_id'], 'Available again'

    print '=====> End Updating Prices'


def add_to_db_process():
    new_dir = data_dir + folder_name + '/' + 'car_details/'

    if not exists(new_dir):
        return

    onlyfiles = [f for f in listdir(new_dir) if isfile(join(new_dir, f))]

    for car_detail_file in onlyfiles:
        if not car_detail_file.endswith('.html'):
            continue
        if car_detail_file.startswith('car_carfax'):
            continue

        parse_file_update_db(car_detail_file)

    if len(unknown_makes) > 0 or len(unknown_locations) > 0:
        send_email_to_technical_administrator(
            "Unknown Makes: " + str(unknown_makes) + " | Unknown Locations: " + str(
                unknown_locations) + ' | Unknown Models: ' + str(unknown_models))
        print "Unknown Makes:"
        print unknown_makes
        print "Unknown Models:"
        print unknown_models
        print "Unknown Locations:"
        print unknown_locations


def parse_file_update_db(car_detail_file, folder_path=None, old=False):
    if folder_path == None:
        folder_path = os.path.join(data_dir, folder_name, 'car_details')

    has_error_so_do_not_save = False

    car_path = os.path.join(folder_path, car_detail_file)
    car_id = car_detail_file.split('.')[0].split('_')[1]  # Retrive car id from file name
    print car_id

    carfax_exist = True
    carfax_filename = 'car_carfax_' + str(car_id) + '.html'
    carfax_path = os.path.join(folder_path, carfax_filename)
    if not exists(carfax_path):
        print >> sys.stderr, 'Does not have carfax', car_id
        carfax_exist = False

    print 'Start reading car page'

    # For Getting Error and Analyze that Remove the Try Catch
    try:
        car_info = parse_vehicle_detail_page(car_path)
    except KeyboardInterrupt:
        sys.exit()
    except:
        print >> sys.stderr, 'Error Occured in parsing car page', car_id
        has_error_so_do_not_save = True
        return

    # print car_info

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
            print >> sys.stderr, 'Error Occured in parsing carfax', car_id

        print 'Reading car carfax is finished'

    try:
        car = Car.objects.get(vin=car_info['VIN'])
        if old == False:
            car.last_updated_time = timezone.localtime(timezone.now())
        car.is_rejected = False
        car.eligible_to_display = False
        print 'UPDATIIIIIIIIIIIIIIIIIIIIIIIIIIIIING CAR'
    except KeyboardInterrupt:
        sys.exit()
    except:
        print 'NEWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW CAR'
        car = Car()

    if old == False:
        car.available_on_ade = True
        car.is_it_available = True

    car.vin = car_info['VIN']
    car.ade_car_id = car_id
    car.car_model = car_info['model']
    car.last_checking = timezone.localtime(timezone.now())
    car.original_price = car_info['price']
    car.year = car_info['year']

    car_info['make'] = car_info['make'].replace('-', ' ')
    if car_info['make'] in ade_make_dict:
        car_info['make'] = ade_make_dict[car_info['make']]

    try:
        make = Make.objects.get(name__iexact=car_info['make'])
        car.make = make

    except KeyboardInterrupt:
        sys.exit()
    except:
        print >> sys.stderr, 'Make Not Found -----> ', car_info['make']
        has_error_so_do_not_save = True
        unknown_makes.add(car_info['make'])

    if 'AutoGrade' in car_info:
        car.grade = float(car_info['AutoGrade'])
    elif 'Grade' in car_info:
        car.grade = float(car_info['Grade'])

    if car.make:
        if car.make.name == 'BMW':
            my_model, my_trim = get_bmw_model_and_trim(car_info['model'])
        else:
            my_model, my_trim = get_model_and_trim(car_info['model'], car.make.name.lower())

        if my_model == None:
            unknown_models.add(car_info['model'])

        car.model = my_model
        car.trim = my_trim

    # Location
    try:
        if 'Processing Location' in car_info and car_info['Processing Location'].strip() != '':
            ade_location = ' '.join(car_info['Processing Location'].split())
        elif 'Location' in car_info and car_info['Location'].strip() != '':
            ade_location = ' '.join(car_info['Location'].split())
        else:
            ade_location = None
            raise Exception('Location not found')

        ade_location = ade_location.strip().replace(' , ', ', ')

        if ade_location in ade_location_dict:
            ade_location = ade_location_dict[ade_location]

        location = Location.objects.get(name__iexact=ade_location)
        car.location = location
    except KeyboardInterrupt:
        sys.exit()
    except:
        unknown_locations.add(ade_location)
        print >> sys.stderr, 'Location is not in database -------->' + ade_location
        has_error_so_do_not_save = True

    if has_error_so_do_not_save == False:
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

        car_detail.detail_html = car_path
        car_detail.vehicle_options = '\n'.join(car_info['options'])
        car_detail.miles = car_info['Current Odometer'].split(' ')[0].replace(',', '')
        car_detail.exterior = car_info['Exterior Color']
        car_detail.interior = car_info['Interior Color']
        car_detail.engine = car_info['Engine']

        # car_detail.odor = car_info['odor'] if 'odor' in car_info else None
        car_detail.msrp = int(
            float(car_info['MSRP'].strip().replace("$", '').replace(',', ''))) if 'MSRP' in car_info and len(
            car_info['MSRP'].strip()) > 0 else None
        # car_detail.announcements = car_info['announcements']
        # car_detail.value_added_options = car_info['value added options']
        # car_detail.drive = car_info['drive']
        # # car_detail.keys = car_info[''],
        #
        # if len(car_info['warranty date']) > 0:
        #     date_set = car_info['warranty date'].split('-')
        #     warranty_date = '20' + date_set[2] + '-' + date_set[0] + '-' + date_set[1]
        #     car_detail.warranty_date = warranty_date

        car_detail.save()

        ###########
        # ade Does not have "Repair"
        ###########

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

                    # # Tires
                    # if 'tires' in car_info:
                    #     tires = Tire.objects.filter(car=car)
                    #     tires.delete()
                    #
                    #     for t in car_info['tires']:
                    #         image = Image(car=car)
                    #         image.link = image_link
                    #         image.save()


def parse_vehicle_detail_page(car_path):
    filename = car_path.split('/')[-1]
    car_id = filename.split('.')[0].split('_')[1]  # Retrive car id from file name

    soup = BeautifulSoup(open(car_path), 'html.parser')

    ans = {}

    ############### Images ##############

    images = []
    images_elements = soup.select('.one img')
    for image_element in images_elements:
        images.append(image_element['src'].replace('_th', ''))

    ans['images'] = images

    ############### Vehicle Title & Price ##############

    try:
        title = soup.find("span", {"id": "vehicle_info_title_ymm"}).text.strip()
        if title == '':
            print >> sys.stderr, 'Error Missing Title: ' + car_path
    except KeyboardInterrupt:
        sys.exit()
    except:
        print >> sys.stderr, 'Error in finding title: ' + car_path

    title = title.split(' ', 2)

    ans['year'] = title[0]
    ans['make'] = title[1]

    if len(title) > 2:
        ans['model'] = title[2]
    else:
        ans['model'] = ''

    price = None

    try:
        price = soup.find("input", {"id": "bidButton_floating"})['value'].strip().split('$')[1].replace(',', '')
    except KeyboardInterrupt:
        sys.exit()
    except:
        pass

    if price == None:
        try:
            price = soup.find("input", {"id": "buyButton_floating"})['value'].strip().split('$')[1].replace(',',
                                                                                                            '')
        except KeyboardInterrupt:
            sys.exit()
        except:
            pass

    ans['price'] = price

    ############### Vehiacle Details ##########

    leftside_details = soup.find("table", {"id": "vdp_top_section_left_table"})
    keys = leftside_details.findAll('td', {"class": 'left'})
    keys_list = []
    for k in keys:
        keys_list.append(k.getText())

    values = leftside_details.findAll('td', {'class': 'right'})
    for ind, v in enumerate(values):
        ans[keys_list[ind][:-1]] = v.getText()
    ########
    rightside_details = soup.find("table", {"id": "vdp_top_section_right_table"})
    # print rightside_details
    keys_list = []
    keys = rightside_details.findAll('td', {"class": 'left'}, id=lambda x: x != 'vdp_grade_label')
    for k in keys:
        keys_list.append(k.getText())

    values = rightside_details.findAll('td', {'class': 'right'})

    for ind, v in enumerate(values):
        ans[keys_list[ind].split(':')[0]] = v.getText()

    ################# Vehicle Information #############

    vehicale_info = soup.find('div', {'id': 'adesaData'})
    info_keys = map(lambda x: x.getText(), vehicale_info.findAll('div', {'class': 'content-item-label'}))
    info_values = map(lambda x: x.getText(), vehicale_info.findAll('div', {'class': 'content-item-value'}))

    for ind, k in enumerate(info_keys):
        if len(info_values) <= ind:
            break
        if k == None or k == '':
            continue

        ans[k[:-1]] = info_values[ind]

    ################### Equipment ###############

    low_eq = soup.find('table', {'id': 'low_value_equipment_table'})
    arr_low = map(lambda x: x.getText(), low_eq.findAll('td'))
    high_eq = soup.find('table', {'id': 'high_value_equipment_table'})
    arr_high = map(lambda x: x.getText(), low_eq.findAll('td'))
    ans['options'] = filter(lambda x: len(x) > 0, arr_low) + filter(lambda x: len(x) > 0, arr_high)

    ################## Inspection Summary #######

    inspection = soup.find('table', {'id': 'inspection-table'})
    ins_keys = map(lambda x: x.getText(), inspection.findAll('td', {'width': '157'}))
    ins_keys = map(lambda x: x[:-1], ins_keys)  # to remove : from end of words
    ins_val = map(lambda x: x.getText(), inspection.findAll('td', {'class': "data-cell"}))
    for ind, k in enumerate(ins_keys):
        ans[k] = ins_val[ind]

    ################ Damages #####################

    inspection = soup.select('table#damages-table')[0]
    rows = inspection.select('tr')
    damages = []

    starter = -1

    for i, r in enumerate(rows):
        if i == 0:
            th_set = r.select('th')
            for j, th in enumerate(th_set):
                if th.string.strip() == 'Region/Area':
                    starter = j
                    break
        else:
            td_set = r.select('td')

            if starter == -1:
                continue

            if td_set[starter].get('class', None) != None:
                continue

            if td_set[starter].string == None or td_set[starter].string == '':
                continue

            arr = map(lambda x: x.text, td_set)
            damages.append(arr[starter:starter + 3])

    ans['damages'] = damages

    ################ Tires #######################

    tires = soup.find('div', {'id': 'tireSection'})
    tire_tbl = tires.find('table')

    if tire_tbl != None:
        rows = tire_tbl.findAll('tr', {'class': 'shade'})
        tires = []
        for r in rows:
            arr = map(lambda x: x.getText(), r.findAll('td'))
            tires.append(arr[1:4])
        ans['tires'] = tires

    return ans


##########################################################################################


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


def get_model_and_trim(title, make):
    models = CarModel.objects.filter(make__name__iexact=make)

    my_model = None
    my_trim = None

    for model in models:
        if model.name.lower() in title.lower():
            if my_model == None or len(model.name) > len(my_model.name):
                my_model = model

    if my_model != None:
        trims = CarTrim.objects.filter(model__name__iexact=my_model.name)

        for trim in trims:
            if trim.name.lower() in title.lower():
                my_trim = trim
                break

    return my_model, my_trim


def send_email_to_technical_administrator(message):
    plaintext = get_template('crawler/email/report_to_admin.txt')
    htmly = get_template('crawler/email/report_to_admin.html')
    d = Context({'message': message})

    subject, from_email = 'Carboi Crawler Failure', 'Carboi Administrator <noreply@carboi.com>'
    to = settings.TECHNICAL_ADMIN_EMAIL + ' ' + '<' + settings.TECHNICAL_ADMIN_EMAIL + '>'
    text_content = plaintext.render(d)
    html_content = htmly.render(d)

    try:
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    except KeyboardInterrupt:
        sys.exit()
    except Exception as e:
        print "A problem occured in sending email to you. Please contact administrator."


def remove_empty_detail_files():
    folder_name = get_latest_search_folder_name()

    new_dir = data_dir + folder_name + '/' + 'car_details/'

    print '=====> Remove Empty Detail Files'

    files = [f for f in listdir(new_dir) if isfile(join(new_dir, f))]

    for car_detail_file in files:
        if not car_detail_file.endswith('.html'):
            continue
        if car_detail_file.startswith('car_carfax'):
            continue

        try:
            parse_vehicle_detail_page(new_dir + car_detail_file)
        except KeyboardInterrupt:
            sys.exit()
        except:
            os.remove(new_dir + car_detail_file)
            print "removed " + new_dir + car_detail_file


def remove_without_carfax():
    folder_name = get_latest_search_folder_name()

    new_dir = data_dir + folder_name + '/' + 'car_details/'

    print '=====> Remove Without Carfax Car files'

    files = [f for f in listdir(new_dir) if isfile(join(new_dir, f))]

    for car_detail_file in files:
        if not car_detail_file.endswith('.html'):
            continue
        if car_detail_file.startswith('car_carfax'):
            continue

        car_id = car_detail_file.split('_')[1].split('.')[0]
        if not exists(new_dir + 'car_carfax_' + car_id + '.html'):
            os.remove(new_dir + car_detail_file)
            print "removed " + new_dir + car_detail_file


def get_driver_status():
    try:
        driver.execute(remote.command.Command.STATUS)
        return "Alive"
    except httplib.BadStatusLine:
        pass
    except (socket.error, httplib.CannotSendRequest):
        return "Dead"
