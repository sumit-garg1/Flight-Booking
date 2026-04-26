from django.db import models

class CountryModel(models.Model):
    country_name = models.CharField(max_length=50, null=True, blank=True)
    country_code = models.CharField(max_length=5, null=True, blank=True)
    region_code = models.CharField(max_length=10, null=True, blank=True)


    def __str__(self):
        return self.country_name or ""


class CityModel(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    country = models.ForeignKey(CountryModel, on_delete=models.CASCADE, related_name='cities', null=True, blank=True)
    iataCode = models.CharField(max_length=6, null=True, blank=True)

    def __str__(self):
        return self.name or ""


class AirportModel(models.Model):
    type=models.CharField(max_length=50,null=True,blank=True)
    sub_type=models.CharField(max_length=50,null=True,blank=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    city = models.ForeignKey(CityModel, on_delete=models.CASCADE, related_name='airports',null=True,blank=True)

    def __str__(self):
        return self.name or ""

    @property
    def iata_code(self):
        return self.city.iataCode



class TimeZoneModel(models.Model):
    airport = models.OneToOneField(AirportModel, on_delete=models.CASCADE, related_name='timezone')
    offset = models.CharField(max_length=6, null=True, blank=True) 
    reference_local_datetime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.airport.name} - {self.offset}"
