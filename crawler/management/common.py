import time, random, requests
from bs4 import BeautifulSoup

from crawler.models import *


def wait_about(approximate_time, variance=7):
    sleep_time = int(random.random() * variance) + approximate_time
    print 'WAIT For ', sleep_time, ' seconds for next Request....'
    time.sleep(sleep_time)


def parse_carfax(carfax_path):
    soup = BeautifulSoup(open(carfax_path), 'html.parser')
    carfax_info = {}

    ownership_text_element = soup.select('#ownershipText')
    if len(ownership_text_element) > 0:
        ownership_text = ownership_text_element[0].string.strip()
        # print ownership_text
        if ownership_text == 'CARFAX 1-Owner':
            carfax_info['ownership'] = {'text': ownership_text, 'number': 1}
        ownership_number_element = soup.select('#ownershipNumber')
        if len(ownership_number_element) > 0:
            ownership_number = int(ownership_number_element[0].string.strip())
            carfax_info['ownership'] = {'text': ownership_text, 'number': ownership_number}
            # print ownership_number
    # print '====='

    lst = ['titleBrand', 'damage', 'odometer', 'serviceRecords']

    for name in lst:
        text_element = soup.select('#' + name + 'Text')
        status_element = soup.select('#' + name + 'Status')
        if len(status_element) > 0 and len(text_element) > 0:
            text = text_element[0].string.strip()
            status = status_element[0]['alt']
            carfax_info[name] = {'text': text, 'status': status}
            # print status
            # print text
            # print '====='

    # Green Check Mark
    # Yellow Warning

    historyRecords_text_element = soup.select('#historyRecordsText')
    historyRecords_number_element = soup.select('#historyRecordsNumber strong')

    if len(historyRecords_text_element) > 0 and len(historyRecords_number_element) > 0:
        historyRecords_text = historyRecords_text_element[0].string.strip()
        historyRecords_number = int(historyRecords_number_element[0].string.strip())
        carfax_info['historyRecords'] = {'text': historyRecords_text, 'number': historyRecords_number}
        # print historyRecords_text
        # print historyRecords_number

    return carfax_info


def get_carfax_object(carfax_info):
    carfax = Carfax()
    ownership = carfax_info.get('ownership')
    if ownership != None:
        carfax.ownership_text = ownership['text']
        carfax.ownership_number = ownership['number']

    title_brand = carfax_info.get('titleBrand')
    if title_brand != None:
        carfax.title_brand_text = title_brand['text']
        carfax.title_brand_status = title_brand['status']

    damage = carfax_info.get('damage')
    if damage != None:
        carfax.damage_text = damage['text']
        carfax.damage_status = damage['status']

    odometer = carfax_info.get('odometer')
    if odometer != None:
        carfax.odometer_text = odometer['text']
        carfax.odometer_status = odometer['status']

    serviceRecords = carfax_info.get('serviceRecords')
    if serviceRecords != None:
        carfax.serviceRecords_text = serviceRecords['text']
        carfax.serviceRecords_status = serviceRecords['status']

    historyRecords = carfax_info.get('historyRecords')
    if historyRecords != None:
        carfax.historyRecords_text = historyRecords['text']
        carfax.historyRecords_number = historyRecords['number']

    return carfax

def fetch_image(vin):
    car = Car.objects.get(vin__iexact=vin)
    year = car.year
    car_model = car.model
    car_trim = car.trim

    response = requests.get(
        'https://api.fuelapi.com/v1/json/vehicle/' + car.vin + '/?api_key=daefd14b-9f2b-4968-9e4d-9d4bb4af01d1')