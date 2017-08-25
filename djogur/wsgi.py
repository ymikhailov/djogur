"""
WSGI config for djogur project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/
"""

import os
import sys

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.append(PROJECT_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djogur.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
