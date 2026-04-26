from django.conf import settings

import sys, os, django

sys.path.append('../')
os.environ['DJANGO_SETTINGS_MODULE'] = 'travel_app.settings'

django.setup()

from amadeus import Client, ResponseError
from airports.models import AirportModel,CityModel,CountryModel





from routes.models import  *


x = FlightOfferModel.objects.filter(destination='MAD')


for index,i in enumerate(x):
    print(i)
    # if index >=10:
    #     break