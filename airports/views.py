from django.shortcuts import render
from airports.models import CountryModel, CityModel, AirportModel, TimeZoneModel
from routes.views import get_flight_offers_for_route,apply_discount
from routes.models import *
import requests
import json
from django.utils.safestring import mark_safe
from django.db.models import Q
import requests

_currency_rate_cache = {}

# Discount mapping based on fare options
DISCOUNT_MAP = {
    "STANDARD": 0.05,   # no discount
    "PREMIUM": 0.10,   # 10% discount
    "BUSINESS": 0.15,  # 15% discount
}

def get_inr_rate(from_currency):
    """
    Returns the conversion rate from `from_currency` to INR.
    Caches results to avoid multiple API calls.
    """
    if from_currency.upper() == "INR":
        return 1.0

    if from_currency in _currency_rate_cache:
        return _currency_rate_cache[from_currency]

    # Try Frankfurter API
    try:
        url = f"https://api.frankfurter.app/latest?from={from_currency}&to=INR"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        rate = res.json().get("rates", {}).get("INR")
        if rate:
            rate = float(rate)
            _currency_rate_cache[from_currency] = rate
            return rate
    except Exception as e:
        print(f"Frankfurter failed ({from_currency}→INR): {e}")

    # Fallback to open.er-api.com
    try:
        url2 = f"https://open.er-api.com/v6/latest/{from_currency}"
        res2 = requests.get(url2, timeout=10)
        res2.raise_for_status()
        data2 = res2.json()
        if data2.get("result") == "success" and "INR" in data2.get("rates", {}):
            rate = float(data2["rates"]["INR"])
            _currency_rate_cache[from_currency] = rate
            return rate
    except Exception as e:
        print(f"Fallback conversion failed ({from_currency}→INR): {e}")

    # Final fallback
    print(f"⚠️ Using fallback rate 1:1 for {from_currency}→INR")
    _currency_rate_cache[from_currency] = 1.0
    return 1.0


def convert_to_inr(amount, from_currency, fare_option="STANDARD"):
    """
    Converts amount from any currency to INR and applies discount
    based on the fare option.
    """
    try:
        rate = get_inr_rate(from_currency)
        price_in_inr = float(amount) * rate

        # Apply discount
        discount = DISCOUNT_MAP.get(fare_option.upper(), 0.0)
        discounted_price = price_in_inr * (1 - discount)

        return round(discounted_price, 2), "INR"
    except Exception as e:
        print(f"Conversion failed ({from_currency}→INR): {e}")
        return round(float(amount), 2), from_currency


def home_view(request):
    """
    Home page: provide airport list for search.
    Allows searching by city or country name.
    """
    search_query = request.GET.get("q", "").strip().lower()

    # Get all airports with related city & country
    airports = AirportModel.objects.select_related("city", "city__country").all()

    # Build airport dict: key = "City, Country", value = IATA code
    airport_dict = {}
    for airport in airports:
        if airport.city and airport.city.iataCode and airport.city.country:
            city_name = airport.city.name or ""
            country_name = airport.city.country.country_name or ""
            display_name = f"{city_name}, {country_name}"
            iata_code = airport.city.iataCode
            airport_dict[display_name] = iata_code

    # If user typed something in search, filter airport_dict keys
    if search_query:
        filtered_dict = {
            k: v for k, v in airport_dict.items()
            if search_query in k.lower()
        }
    else:
        filtered_dict = airport_dict

    context = {
        "airport_dict": filtered_dict,
        "search_query": request.GET.get("q", "")
    }

    return render(request, "home.html", context)

def airport_routes_view(request):
    from_airport_code = request.GET.get("from_airport", "").strip().upper()
    to_airport_code = request.GET.get("to_airport", "").strip().upper()
    departure_date = request.GET.get("departure_date", "").strip()

    flight_offers = []
    error_message = None

    if from_airport_code and to_airport_code:
        success, result = get_flight_offers_for_route(
            origin=from_airport_code,
            destination=to_airport_code,
            departure_date=departure_date or None,
        )

        if success and result:
            seen = set()
            for r in result:
                segments = list(r.route_path.routes.select_related("origin__city", "destination__city").all())
                if not segments:
                    continue

                first_seg = segments[0]
                last_seg = segments[-1]

                converted_price, converted_currency = convert_to_inr(r.price_total, r.currency)

                route_iatas = [seg.origin.city.iataCode for seg in segments if seg.origin and seg.origin.city]
                route_iatas.append(last_seg.destination.city.iataCode if last_seg.destination and last_seg.destination.city else "Unknown")
                route_str = " → ".join(route_iatas)

                offer_info = {
                    "id": r.id,
                    "route": route_str,
                    "flight_numbers": " → ".join([f"{seg.airline_name} ({seg.airline_code} {seg.flight_number})" for seg in segments]),
                    "from": first_seg.origin,
                    "to": last_seg.destination,
                    "departure": first_seg.departure_time,
                    "arrival": last_seg.arrival_time,
                    "duration": last_seg.duration.replace("PT", "") if last_seg.duration else "",
                    "price": f"₹{converted_price:,.2f}",
                    "stops": max(len(segments) - 1, 0),
                }

                key = f"{route_str}-{converted_price}"
                if key in seen:
                    continue
                seen.add(key)

                flight_offers.append(offer_info)

            if not flight_offers:
                error_message = f"No flights available from {from_airport_code} to {to_airport_code}."
        else:
            error_message = f"Amadeus API Error: {result or 'No routes available for this search'}"

    elif from_airport_code or to_airport_code:
        error_message = "Please enter both 'From' and 'To' airport codes to search."

    airport_dict_dynamic = {
        a.city.name: a.city.iataCode
        for a in AirportModel.objects.select_related("city").all()
        if a.city and a.city.iataCode
    }

    # Get unique airlines for filter
    unique_airlines = set()
    for offer in flight_offers:
        airline_name = offer['flight_numbers'].split('(')[0].strip()
        unique_airlines.add(airline_name)

    context = {
        "airport_dict": airport_dict_dynamic,
        "from_airport": from_airport_code,
        "to_airport": to_airport_code,
        "departure_date": departure_date,
        "flight_offers": flight_offers,
        "error": error_message,
        "unique_airlines": list(unique_airlines),
    }

    return render(request, "airport_routes.html", context)
airport_dict = {
    "ALBACETE": "ABC",
    "LANZAROTE": "ACE",
    "MALAGA": "AGP",
    "ALGHERO": "AHO",
    "ALICANTE": "ALC",
    "ALGIERS": "ALG",
    "AMMAN": "AMM",
    "AMSTERDAM": "AMS",
    "ASUNCION": "ASU",
    "ATHENS": "ATH",
    "ATLANTA": "ATL",
    "ABU DHABI": "AUH",
    "SAMANA": "AZS",
    "BACAU": "BCM",
    "BARCELONA": "BCN",
    "BELGRADE": "BEG",
    "BERLIN": "BER",
    "BEIRUT": "BEY",
    "BERGEN": "BGO",
    "BILBAO": "BIO",
    "BEIJING": "BJS",
    "BADAJOZ": "BJZ",
    "BOLOGNA": "BLQ",
    "BORDEAUX": "BOD",
    "BOGOTA": "BOG",
    "BOSTON": "BOS",
    "BARI": "BRI",
    "BRISTOL": "BRS",
    "BRUSSELS": "BRU",
    "BUDAPEST": "BUD",
    "BUENOS AIRES": "BUE",
    "BUCHAREST": "BUH",
    "CAGLIARI": "CAG",
    "CAIRO": "CAI",
    "COCHABAMBA": "CBB",
    "CARACAS": "CCS",
    "KERKYRA": "CFU",
    "CHICAGO": "CHI",
    "CLUJ NAPOCA": "CLJ",
    "CALI": "CLO",
    "CHARLOTTE": "CLT",
    "CASABLANCA": "CMN",
    "COPENHAGEN": "CPH",
    "CRAIOVA": "CRA",
    "CATANIA": "CTA",
    "CANCUN": "CUN",
    "DUBROVNIK": "DBV",
    "DALLAS": "DFW",
    "DAKAR": "DKR",
    "DOHA": "DOH",
    "DUBLIN": "DUB",
    "DUESSELDORF": "DUS",
    "DUBAI": "DXB",
    "DELHI": "DEL",
    "FRANKFURT": "FRA",
    "SYDNEY": "SYD",
    "PARIS": "PAR",
    "ROME": "ROM",
    "LONDON": "LON",
    "NEW YORK": "NYC",
    "TOKYO": "TYO",
    "TORONTO": "YTO",
    "ZURICH": "ZRH",
}
# def convert_to_inr(amount, from_currency):
#     """
#     Converts any currency amount to INR using two sources:
#     1. Frankfurter.app (primary)
#     2. open.er-api.com (fallback)
#     """
#     if from_currency == "INR":
#         return round(float(amount), 2), "INR"

#     # 1️⃣ Try Frankfurter first
#     try:
#         url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_currency}&to=INR"
#         res = requests.get(url, timeout=5)
#         data = res.json()
#         if "rates" in data and "INR" in data["rates"]:
#             return round(data["rates"]["INR"], 2), "INR"
#     except Exception as e:
#         print(f"Frankfurter failed ({from_currency}→INR): {e}")

#     # 2️⃣ Fallback to open.er-api.com
#     try:
#         url2 = f"https://open.er-api.com/v6/latest/{from_currency}"
#         res2 = requests.get(url2, timeout=5)
#         data2 = res2.json()
#         if data2.get("result") == "success" and "INR" in data2["rates"]:
#             rate = data2["rates"]["INR"]
#             converted = round(float(amount) * rate, 2)
#             return converted, "INR"
#     except Exception as e:
#         print(f"Fallback conversion failed ({from_currency}→INR): {e}")

#     # 3️⃣ Final fallback (return same)
#     return round(float(amount), 2), from_currency