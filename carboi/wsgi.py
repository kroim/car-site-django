"""
WSGI config for carboi project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os
import dotenv

from django.core.wsgi import get_wsgi_application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv.read_dotenv(BASE_DIR + "/.env")
environment = os.environ.get("CARBOI_ENV", "development")

os.environ["DJANGO_SETTINGS_MODULE"] = "carboi.settings.{}".format(environment)

application = get_wsgi_application()
