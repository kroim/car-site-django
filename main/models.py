from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
import crawler

class FAQCategory(models.Model):
    name = models.CharField(max_length=255)
    fa_icon = models.CharField(max_length=63)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ('order', 'id', )

    def __unicode__(self):
        return self.name

class FAQ(models.Model):
    faq_category = models.ForeignKey('FAQCategory')
    question = models.CharField(max_length=1023)
    answer = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ('order', 'id', )

    def __unicode__(self):
        return self.question

class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    car = models.ManyToManyField('crawler.Car', through='UserCarRecommendation', blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    '''todo: change phone field type to something smarter, 
       maybe charfield with regex or regexfield'''

    def __unicode__(self):
        return self.user.username

'''Hookup create and save to our account model'''
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Account.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.account.save()
    except ObjectDoesNotExist:
        pass

'''Create model to govern manytomany relationship'''
class UserCarRecommendation(models.Model):
    car = models.ForeignKey('crawler.Car',blank=True,null=True)
    account = models.ForeignKey(Account,blank=True,null=True)
    #additional fields will be added later

    def __unicode__(self):
        return str(self.account) + ": " + str(self.car.id)