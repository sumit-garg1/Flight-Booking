# from django.conf import settings
# import sys, os, django, time

# sys.path.append('../')
# os.environ['DJANGO_SETTINGS_MODULE'] = 'airline_reservation.settings'
# django.setup()

# from amadeus import Client, ResponseError
# from airports.models import AirportModel, CityModel, CountryModel

# # ---------------------- Amadeus client ----------------------
# amadeus = Client(
#     client_id=settings.CLIENT_ID,
#     client_secret=settings.CLIENT_SECRET
# )


# # ---------------------- Fetch Routes ----------------------
# def get_airport_routes(airport_code):
#     print(f"\n🌍 Fetching routes for: {airport_code}")
#     try:
#         res = amadeus.airport.direct_destinations.get(departureAirportCode=airport_code)
#         data = res.data or []
#         print(f"✅ Found {len(data)} destinations for {airport_code}")
#         return True, data
#     except ResponseError as e:
#         print(f"❌ Error fetching routes for {airport_code}: {e}")
#         return False, []


# # ---------------------- Create Airport ----------------------
# def create_airport(data):
#     arr = data.get("arrivalAirport") or data
#     if not arr or not arr.get("iataCode"):
#         return None

#     iata = arr.get("iataCode")
#     name = arr.get("name")

#     print(f"✈️  Creating airport/city: {name} ({iata})")

#     # Country
#     country_data = arr.get("country") or arr.get("address") or {}
#     country, _ = CountryModel.objects.get_or_create(
#         country_code=country_data.get("code") or country_data.get("countryCode"),
#         defaults={
#             "country_name": country_data.get("name") or country_data.get("countryName"),
#             "region_code": country_data.get("regionCode"),
#         },
#     )

#     # City
#     city, _ = CityModel.objects.get_or_create(
#         name=arr.get("name"),
#         iataCode=iata,
#         country=country,
#     )

#     # Airport
#     airport, _ = AirportModel.objects.get_or_create(
#         name=name,
#         type=arr.get("type", "location"),
#         sub_type=arr.get("subtype", "city"),
#         latitude=arr.get("geoCode", {}).get("latitude"),
#         longitude=arr.get("geoCode", {}).get("longitude"),
#         city=city,
#     )

#     return airport
# SEED_AIRPORTS = [
    
#     {"iata": "JFK", "name": "John F Kennedy International Airport", "country_code": "US", "country_name": "United States"},
# ]

# def seed_airports():
#     for a in SEED_AIRPORTS:
#         country, _ = CountryModel.objects.get_or_create(
#             country_code=a["country_code"],
#             defaults={"country_name": a["country_name"]},
#         )
#         city, _ = CityModel.objects.get_or_create(
#             name=a["name"],
#             iataCode=a["iata"],
#             country=country,
#         )
#         AirportModel.objects.get_or_create(
#             name=a["name"],
#             city=city,
#         )
#     print(f"✅ Seeded {len(SEED_AIRPORTS)} initial airports.")

# # ---------------------- Main Expansion Logic ----------------------
# def expand_airports(max_depth=2):
#     visited = set()
#     depth = 0

#     while depth < max_depth:
#         print(f"\n===== 🌐 EXPANSION ROUND {depth+1}/{max_depth} =====")

#         airports = AirportModel.objects.exclude(city__iataCode__in=visited)
#         if not airports.exists():
#             print("No new airports left to explore.")
#             break

#         for airport in airports:
#             code = airport.city.iataCode
#             if not code or code in visited:
#                 continue

#             visited.add(code)

#             success, routes = get_airport_routes(code)
#             if success:
#                 for dest in routes:
#                     create_airport(dest)

#             # Avoid Amadeus rate limit (approx. 30 requests/min)
#             time.sleep(2)

#         depth += 1

#     print("\n✅ Done expanding airports!")


# # ---------------------- Run ----------------------
# if __name__ == "__main__":
#     if AirportModel.objects.count() == 0:
#         seed_airports()
#     print(f"Total airports before expansion: {AirportModel.objects.count()}")
#     expand_airports(max_depth=3)
#     print(f"Total airports after expansion: {AirportModel.objects.count()}")


from django.conf import settings
import sys, os, django, random
from datetime import datetime, timedelta

sys.path.append('../')
os.environ['DJANGO_SETTINGS_MODULE']='airline_reservation.settings'
django.setup()

from airports.models import AirportModel, CityModel, CountryModel
from routes.models import FlightOfferModel, RoutePathModel, RoutesModel


# ================= AIRPORTS =================

SEED_AIRPORTS = [

("DEL","Delhi","IN","India"),
("BOM","Mumbai","IN","India"),
("BLR","Bangalore","IN","India"),
("HYD","Hyderabad","IN","India"),
("MAA","Chennai","IN","India"),
("CCU","Kolkata","IN","India"),
("LKO","Lucknow","IN","India"),
("PNQ","Pune","IN","India"),
("AMD","Ahmedabad","IN","India"),
("JAI","Jaipur","IN","India"),
("GOI","Goa","IN","India"),
("IXC","Chandigarh","IN","India"),

("DXB","Dubai","AE","UAE"),
("AUH","Abu Dhabi","AE","UAE"),
("DOH","Doha","QA","Qatar"),
("MCT","Muscat","OM","Oman"),

("LHR","London","GB","UK"),
("CDG","Paris","FR","France"),
("FRA","Frankfurt","DE","Germany"),
("AMS","Amsterdam","NL","Netherlands"),
("MAD","Madrid","ES","Spain"),

("JFK","New York","US","USA"),
("LAX","Los Angeles","US","USA"),
("SFO","San Francisco","US","USA"),

("SIN","Singapore","SG","Singapore"),
("BKK","Bangkok","TH","Thailand"),
("KUL","Kuala Lumpur","MY","Malaysia"),
("NRT","Tokyo","JP","Japan"),
]


AIRLINES = [
("AI","Air India"),
("6E","IndiGo"),
("UK","Vistara"),
("SG","SpiceJet"),
("EK","Emirates"),
("QR","Qatar Airways"),
("BA","British Airways"),
("LH","Lufthansa"),
("SQ","Singapore Airlines"),
]


# ================= SEED =================

def seed_airports():

    if AirportModel.objects.exists():
        print("Airports already exist")
        return

    print("Seeding airports...")

    for code,city_name,country_code,country_name in SEED_AIRPORTS:

        country,_=CountryModel.objects.get_or_create(
            country_code=country_code,
            defaults={
                "country_name":country_name
            }
        )

        city,_=CityModel.objects.get_or_create(
            iataCode=code,
            defaults={
                "name":city_name,
                "country":country
            }
        )

        AirportModel.objects.get_or_create(
            city=city,
            defaults={
                "name":f"{city_name} Airport",
                "type":"airport",
                "sub_type":"city"
            }
        )

    print(
        f"{AirportModel.objects.count()} airports ready"
    )


# ================= CLEAR =================

def clear_old_data():

    print("Deleting old routes/flights...")

    FlightOfferModel.objects.all().delete()
    RoutesModel.objects.all().delete()
    RoutePathModel.objects.all().delete()

    print("Old data cleared")


# ================= FLIGHT GENERATOR =================

def generate_dummy_flights():

    airports=list(
        AirportModel.objects.all()
    )

    if len(airports)<2:
        print("Need at least 2 airports")
        return

    total=0

    print("Generating flights...")

    for origin in airports:

        for destination in airports:

            if origin==destination:
                continue

            print(
              f"{origin.iata_code} -> {destination.iata_code}"
            )

            # 10 days coverage
            for day in range(1,11):

                base_date=(
                    datetime.now()
                    + timedelta(days=day)
                )

                # 2 flights daily per route
                for i in range(2):

                    # IMPORTANT:
                    # new route path PER FLIGHT
                    route_path=RoutePathModel.objects.create(
                        name=(
                           f"{origin.iata_code}"
                           f" -> "
                           f"{destination.iata_code}"
                        )
                    )

                    code,name=random.choice(
                        AIRLINES
                    )

                    departure_time=base_date.replace(
                        hour=random.randint(5,22),
                        minute=random.choice(
                           [0,15,30,45]
                        ),
                        second=0,
                        microsecond=0
                    )

                    duration=random.randint(
                        1,6
                    )

                    arrival_time=(
                        departure_time+
                        timedelta(hours=duration)
                    )

                    price=random.randint(
                        3000,25000
                    )

                    stops=random.choice(
                        [0,0,0,1] # mostly direct
                    )


                    # one offer
                    FlightOfferModel.objects.create(
                        origin=origin,
                        destination=destination,
                        route_path=route_path,
                        price_total=str(price),
                        currency="INR",
                        stops=stops,
                        departure_date=base_date.date()
                    )


                    # one segment only
                    RoutesModel.objects.create(
                        route_path=route_path,
                        origin=origin,
                        destination=destination,
                        airline_code=code,
                        airline_name=name,
                        flight_number=str(
                            random.randint(
                                100,9999
                            )
                        ),
                        duration=f"{duration}H",
                        departure_time=departure_time,
                        arrival_time=arrival_time
                    )

                    total+=1

    print(
      f"\nDONE. Flights created: {total}"
    )


# ================= RUN =================

if __name__=="__main__":

    seed_airports()

    print(
       f"Airports: "
       f"{AirportModel.objects.count()}"
    )

    clear_old_data()

    generate_dummy_flights()