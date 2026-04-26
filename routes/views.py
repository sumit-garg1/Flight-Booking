# routes/views.py
from uuid import uuid4
from datetime import datetime, timedelta
from django.conf import settings
from django.db import transaction
from amadeus import Client, ResponseError
from airports.models import AirportModel, CityModel
from .models import FlightOfferModel, RoutePathModel, RoutesModel

amadeus = Client(
    client_id=settings.CLIENT_ID,
    client_secret=settings.CLIENT_SECRET
)


def get_flight_offers_for_route(origin, destination, departure_date=None):
    """
    Fetch flight offers from Amadeus or cache.
    Stores basic flight data in FlightOfferModel with valid IDs.
    """
    try:
        if not departure_date:
            departure_date = (datetime.today() + timedelta(days=3)).strftime('%Y-%m-%d')

        print(f"Searching flights: {origin} → {destination} on {departure_date}")

        # Validate airports exist
        try:
            origin_airport = AirportModel.objects.get(city__iataCode=origin)
            destination_airport = AirportModel.objects.get(city__iataCode=destination)
        except AirportModel.DoesNotExist:
            return False, f"Airport not found: {origin} or {destination}"

        # Check cached offers
        cached_offers = FlightOfferModel.objects.filter(
            origin__city__iataCode=origin,
            destination__city__iataCode=destination
        )

        if cached_offers.exists():
            print("Using cached flight offers from database.")
            return True, cached_offers

        # Fresh API call
        print("Fetching fresh data from Amadeus API...")
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=1
        )

        all_airline_codes = set()
        all_iata_codes = set()
        flight_data = []

        # Process each offer
        for offer in response.data:
            itineraries = offer.get("itineraries", [])
            if not itineraries:
                continue

            route_path_obj = RoutePathModel(
                name=f"{origin} → {destination} #{uuid4().hex[:8]}"
            )
            segments_list = []

            for itinerary in itineraries:
                segments = itinerary.get("segments", [])
                for seg in segments:
                    dep_iata = seg["departure"]["iataCode"]
                    arr_iata = seg["arrival"]["iataCode"]

                    if not dep_iata or not arr_iata or len(dep_iata) != 3 or len(arr_iata) != 3:
                        print(f"Skipping invalid segment: {dep_iata} → {arr_iata}")
                        continue

                    segments_list.append(seg)
                    all_iata_codes.update([dep_iata, arr_iata])
                    all_airline_codes.add(seg["carrierCode"])

            if len(segments_list) > 6:
                print(f"Skipping long route: {len(segments_list)-1} stops")
                continue

            flight_data.append({
                "offer": offer,
                "route_path_obj": route_path_obj,
                "segments": segments_list
            })

        # Preload cities/airports
        existing_cities = {c.iataCode: c for c in CityModel.objects.filter(iataCode__in=all_iata_codes)}
        existing_airports = {a.city.iataCode: a for a in AirportModel.objects.filter(city__iataCode__in=all_iata_codes)}

        def get_or_create_city(iata):
            return existing_cities.get(iata) or CityModel.objects.create(iataCode=iata)

        def get_or_create_airport(city_obj, iata):
            return existing_airports.get(iata) or AirportModel.objects.create(
                city=city_obj, name=iata, type="airport", sub_type="city"
            )

        # Fetch airline names
        airline_names = {}
        try:
            if all_airline_codes:
                airline_resp = amadeus.reference_data.airlines.get(
                    airlineCodes=",".join(all_airline_codes)
                )
                for item in airline_resp.data:
                    code = item.get("iataCode")
                    name = item.get("businessName") or item.get("commonName") or code
                    airline_names[code] = name
        except Exception as e:
            print("Airline lookup failed:", e)

        # Save models to DB
        with transaction.atomic():
            # Save RoutePathModel individually to get IDs
            for item in flight_data:
                route_path = item["route_path_obj"]
                route_path.save()
            
            # Save FlightOfferModel individually to get IDs
            for item in flight_data:
                route_path = item["route_path_obj"]
                segments = item["segments"]
                offer = item["offer"]

                # Create FlightOfferModel instance
                price = offer.get("price", {})
                flight_offer = FlightOfferModel(
                    origin=origin_airport,
                    destination=destination_airport,
                    route_path=route_path,
                    price_total=price.get("total", ""),
                    currency=price.get("currency", ""),
                    stops=max(0, len(segments) - 1),
                    offer_json=offer,  # ✅ Save full Amadeus offer JSON

                )
                flight_offer.save()  # ✅ ensures flight_offer.id exists

                # Save RoutesModel for segments
                for seg in segments:
                    dep_iata = seg["departure"]["iataCode"]
                    arr_iata = seg["arrival"]["iataCode"]

                    dep_city = get_or_create_city(dep_iata)
                    arr_city = get_or_create_city(arr_iata)
                    dep_airport = get_or_create_airport(dep_city, dep_iata)
                    arr_airport = get_or_create_airport(arr_city, arr_iata)

                    airline_code = seg["carrierCode"]
                    airline_name = airline_names.get(airline_code, airline_code)

                    RoutesModel.objects.create(
                        route_path=route_path,
                        origin=dep_airport,
                        destination=arr_airport,
                        airline_code=airline_code,
                        airline_name=airline_name,
                        flight_number=seg["number"],
                        duration=seg.get("duration", "").replace("PT", ""),
                        departure_time=seg["departure"]["at"],
                        arrival_time=seg["arrival"]["at"],
                    )

        print(f"Saved {len(flight_data)} new offers to DB.")

        # Return fresh cache
        new_cache = FlightOfferModel.objects.filter(
            origin__city__iataCode=origin,
            destination__city__iataCode=destination
        )
        return True, new_cache

    except ResponseError as error:
        error_msg = f"Amadeus API Error: {error}"
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        return False, error_msg

def apply_discount(price, fare_option="STANDARD", fare_basis=None, branded_fare=None):
    """
    Apply discount based on fare_option, fare_basis, or branded_fare.
    """
    discount_map = {
        "STANDARD": 0,
        "PREMIUM": 0.10,
        "BUSINESS": 0.15,
        "SPANISH_RESIDENT": 0.75,
        "AIR_FRANCE_DOMESTIC": 0.10,
        "AIR_FRANCE_COMBINED": 0.08,
        "AIR_FRANCE_METROPOLITAN": 0.12,
    }

    key = (branded_fare or fare_basis or fare_option or "STANDARD").upper()
    discount = discount_map.get(key, 0)

    discounted_price = price * (1 - discount)
    return round(discounted_price, 2)
