from __future__ import unicode_literals

from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils import timezone

import managers
import random


class Car(models.Model):
    mo_car_id = models.IntegerField(null=True, blank=True)
    ove_car_id = models.IntegerField(null=True, blank=True)
    ade_car_id = models.IntegerField(null=True, blank=True)
    bg_car_id = models.IntegerField(null=True, blank=True)
    vin = models.CharField(max_length=31)
    stock_number = models.CharField(max_length=31, null=True, blank=True)
    make = models.ForeignKey('Make', null=True, blank=True)
    model = models.ForeignKey('CarModel', null=True, blank=True)
    trim = models.ForeignKey('CarTrim', null=True, blank=True)
    car_model = models.CharField(max_length=255)
    original_price = models.IntegerField(null=True, blank=True)
    final_price = models.IntegerField(null=True, blank=True)
    year = models.SmallIntegerField(null=True, blank=True)
    location = models.ForeignKey('Location', null=True, blank=True)
    grade = models.FloatField(null=True, blank=True)
    last_checking = models.DateTimeField()
    is_it_available = models.BooleanField(default=True)
    available_on_mo = models.BooleanField(default=False)
    available_on_bg = models.BooleanField(default=False)
    available_on_ove = models.BooleanField(default=False)
    available_on_ade = models.BooleanField(default=False)
    mo_removed_at = models.DateTimeField(null=True, blank=True)
    bg_removed_at = models.DateTimeField(null=True, blank=True)
    ove_removed_at = models.DateTimeField(null=True, blank=True)
    ade_removed_at = models.DateTimeField(null=True, blank=True)
    last_updated_time = models.DateTimeField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    rejection_reason = models.CharField(max_length=1023, null=True, blank=True)
    eligible_to_display = models.BooleanField(default=False)
    removed_permanently = models.BooleanField(default=False)
    remain_permatently = models.BooleanField(default=False)
    remain_until = models.DateTimeField(null=True, blank=True)
    unique_customer_link = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    objects = managers.CarManager()
    
    def __unicode__(self):
        return str(self.id)

    def save(self, *args, **kwargs):
        if self.stock_number == None:
            self.stock_number = self.generate_stock_number()
        super(Car, self).save(*args, **kwargs)

    def is_available_eligible(self):
        return (self.is_it_available == True\
                or (self.remain_until != None and self.remain_until > timezone.now())\
                or self.remain_permatently == True)\
               and self.is_rejected == False and self.eligible_to_display == True and self.make.is_visible == True\
               and self.removed_permanently == False

    def generate_stock_number(self):
        return chr(65 + int(random.random() * 26)) + chr(65 + int(random.random() * 26)) + str(
            int(random.random() * 10)) + str(int(random.random() * 10)) + str(int(random.random() * 10)) + str(
            int(random.random() * 10))

    def generate_unique_cutomer_link(self):
        string = []
        id_str = str(self.id)
        chars_count = 12
        mod = chars_count / len(id_str)
        for i in xrange(12):
            string.append(chr(97 + int(random.random() * 26)))

        return ''.join(string[:8]) + id_str + ''.join(string[8:])

    def stock_image(self):
        year = self.year
        car_model = self.model
        car_trim = self.trim

        stock_image_infos = StockImageInfo.objects.filter(
            Q(model=car_model) & (Q(trim=None) | Q(trim=car_trim)) & Q(year=year) & Q(stock_image__view_type='F') & Q(
                stock_image__colors__name__iexact=self.cardetail.exterior))

        if len(stock_image_infos) > 0:
            for stock_image_info in stock_image_infos:
                if stock_image_info.trim != None:
                    return stock_image_info.stock_image.image.url

            return stock_image_infos.first().stock_image.image.url

        return static('img/no_image.png')


class CarDetail(models.Model):
    car = models.OneToOneField('Car')
    detail_html = models.FilePathField()
    vehicle_options = models.TextField(null=True, blank=True)
    miles = models.IntegerField(null=True, blank=True)
    exterior = models.CharField(max_length=255, null=True, blank=True)
    interior = models.CharField(max_length=255, null=True, blank=True)
    engine = models.CharField(max_length=255, null=True, blank=True)
    odor = models.CharField(max_length=255, null=True, blank=True)
    msrp = models.IntegerField(null=True, blank=True)
    announcements = models.CharField(max_length=1000, null=True, blank=True)
    value_added_options = models.CharField(max_length=1000, null=True, blank=True)
    warranty_date = models.DateField(null=True, blank=True)
    drive = models.CharField(max_length=255, null=True, blank=True)
    keys = models.CharField(max_length=255, null=True, blank=True)


class Location(models.Model):
    name = models.CharField(max_length=255)
    shipping_cost = models.IntegerField(default=0)

    def __unicode__(self):
        return self.name


class Make(models.Model):
    name = models.CharField(max_length=255)
    fuel_name = models.CharField(max_length=255)
    is_visible = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name


class CarModel(models.Model):
    name = models.CharField(max_length=255)
    fuel_name = models.CharField(max_length=255)
    make = models.ForeignKey('Make')

    def __unicode__(self):
        return self.name + ', ' + self.make.name


class CarTrim(models.Model):
    name = models.CharField(max_length=255)
    model = models.ForeignKey('CarModel')

    def __unicode__(self):
        return self.name + ', ' + self.model.name + ', ' + self.model.make.name


class Tire(models.Model):
    TIRE_CHOICES = (
        ('LFRNT', 'LFRNT'),
        ('LREAR', 'LREAR'),
        ('RFRNT', 'RFRNT'),
        ('RREAR', 'RREAR'),
        ('SPARE', 'SPARE'),
    )

    car = models.ForeignKey('Car')
    type = models.CharField(max_length=31, choices=TIRE_CHOICES)
    tread = models.CharField(max_length=31, null=True, blank=True)
    brand = models.CharField(max_length=31, null=True, blank=True)
    size = models.CharField(max_length=31, null=True, blank=True)


class Repair(models.Model):
    car = models.ForeignKey('Car')
    repaired = models.CharField(max_length=255)
    condition = models.CharField(max_length=255, null=True, blank=True)
    severity = models.CharField(max_length=255, null=True, blank=True)
    repair_type = models.CharField(max_length=255, null=True, blank=True)


class Damage(models.Model):
    car = models.ForeignKey('Car')
    part = models.CharField(max_length=255, null=True, blank=True)
    condition = models.CharField(max_length=255, null=True, blank=True)
    severity = models.CharField(max_length=255, null=True, blank=True)
    estimated_price = models.IntegerField(null=True, blank=True)
    effective_damage_rule = models.ForeignKey('DamageRule', null=True, blank=True)
    mannual = models.NullBooleanField(null=True, blank=True)


class Key(models.Model):
    car = models.ForeignKey('Car')
    name = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)


class Image(models.Model):
    car = models.ForeignKey('Car')
    link = models.URLField()
    show_to_customer = models.BooleanField(default=True)


class StockImageInfo(models.Model):
    stock_image = models.ForeignKey('StockImage')
    model = models.ForeignKey('CarModel')
    trim = models.ForeignKey('CarTrim', null=True, blank=True)
    year = models.IntegerField()


class StockImage(models.Model):
    VIEW_CHOICES = (
        ('F', 'FRONT'),
        ('B', 'BACK'),
        ('S', 'SIDE'),
    )

    VIEW_CHOICES = (
        ('F', 'FRONT'),
        ('B', 'BACK'),
        ('S', 'SIDE'),
    )

    image = models.ImageField(upload_to='stock_images/')
    view_type = models.CharField(max_length=7, choices=VIEW_CHOICES)
    colors = models.ManyToManyField('Color')


class Color(models.Model):
    name = models.CharField(max_length=127)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Contact(models.Model):
    car = models.ForeignKey('Car')
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __unicode__(self):
        return self.first_name + ' ' + self.last_name + ' ' + str(self.created_at)


class DamageRule(models.Model):
    part = models.CharField(max_length=2000, default='.*')
    condition = models.CharField(max_length=2000, default='.*')
    severity = models.CharField(max_length=2000, default='.*')
    car_model = models.CharField(max_length=2000, default='.*')
    price = models.IntegerField()
    mannual = models.BooleanField(default=False)

    def __unicode__(self):
        return self.part + ' ' + self.condition + ' ' + self.severity + ' ' + self.car_model + ' ' + str(self.price)


class Carfax(models.Model):
    car = models.OneToOneField('Car', null=True, blank=True)
    ownership_text = models.CharField(max_length=255, null=True, blank=True)
    ownership_number = models.IntegerField(null=True, blank=True)
    title_brand_text = models.CharField(max_length=255, null=True, blank=True)
    title_brand_status = models.CharField(max_length=255, null=True, blank=True)
    damage_text = models.CharField(max_length=255, null=True, blank=True)
    damage_status = models.CharField(max_length=255, null=True, blank=True)
    odometer_text = models.CharField(max_length=255, null=True, blank=True)
    odometer_status = models.CharField(max_length=255, null=True, blank=True)
    serviceRecords_text = models.CharField(max_length=255, null=True, blank=True)
    serviceRecords_status = models.CharField(max_length=255, null=True, blank=True)
    historyRecords_text = models.CharField(max_length=255, null=True, blank=True)
    historyRecords_number = models.IntegerField(null=True, blank=True)

    def is_clean(self):
        if self.title_brand_status != None and self.title_brand_status != 'Green Check Mark':
            return False
        if self.damage_status != None and self.damage_status != 'Green Check Mark':
            return False
        if self.odometer_status != None and self.odometer_status != 'Green Check Mark':
            return False
        if self.serviceRecords_status != None and self.serviceRecords_status != 'Green Check Mark':
            return False
        return True


class Crawler(models.Model):
    STATUS_CHOICES = (
        ('RUNNING', 'RUNNING'),
        ('IDLE', 'IDLE'),
    )

    name = models.CharField(max_length=255)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
    last_run = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.name


@receiver(post_save, sender=Car)
def set_customer_link(sender, instance, created, **kwargs):
    if instance.unique_customer_link == None:
        instance.unique_customer_link = instance.generate_unique_cutomer_link()
        instance.save()
