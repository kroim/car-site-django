from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
environment = os.environ.get("CARBOI_ENV", "development")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carboi.settings.{}".format(environment))

app = Celery('carboi')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()