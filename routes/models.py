from django.db import models
from airports.models import AirportModel


class RoutePathModel(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name or f"RoutePath {self.id}"


class RoutesModel(models.Model):
    route_path = models.ForeignKey(RoutePathModel, on_delete=models.CASCADE, related_name='routes')
    origin = models.ForeignKey(AirportModel, on_delete=models.CASCADE, related_name='route_origin')
    destination = models.ForeignKey(AirportModel, on_delete=models.CASCADE, related_name='route_destination')
    airline_code = models.CharField(max_length=10)
    airline_name = models.CharField(max_length=100, blank=True, null=True)  # 👈 add this line
    flight_number = models.CharField(max_length=10)
    duration = models.CharField(max_length=50)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    def __str__(self):
        return f"{self.origin.iata_code} → {self.destination.iata_code} ({self.airline_code}{self.flight_number})"


class FlightOfferModel(models.Model):
    origin = models.ForeignKey(AirportModel, on_delete=models.CASCADE, related_name='offer_origin')
    destination = models.ForeignKey(AirportModel, on_delete=models.CASCADE, related_name='offer_destination')
    route_path = models.ForeignKey(RoutePathModel, on_delete=models.CASCADE, related_name='flight_offers', null=True, blank=True)
    price_total = models.CharField(max_length=20)
    departure_date = models.DateField(
    null=True,
    blank=True)
    currency = models.CharField(max_length=10)
    stops = models.IntegerField(default=0)
    offer_json = models.JSONField(default=dict, blank=True, null=True)
    def __str__(self):
        if self.route_path and self.route_path.routes.exists():
            first = self.route_path.routes.first()
            last = self.route_path.routes.last()
            return f"{first.origin.iata_code} → {last.destination.iata_code} | {self.price_total} {self.currency}"
        return f"{self.origin.iata_code} → {self.destination.iata_code} | {self.price_total} {self.currency}"
