from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from amadeus import Client, ResponseError
from routes.models import FlightOfferModel
from airports.views import convert_to_inr
import json
import hashlib
import uuid
from django.contrib.auth.models import User

from .models import *
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages

# ====================== AMADEUS CLIENT SETUP ======================
amadeus = Client(client_id=settings.CLIENT_ID, client_secret=settings.CLIENT_SECRET)


# ====================== DISCOUNT LOGIC ======================
def apply_discount(price_inr, fare_option="STANDARD", fare_basis=None, fare_types=None):
    discount = 0
    reasons = []

    fare_option = fare_option.upper()
    if fare_option == "PREMIUM":
        discount += 5
        reasons.append("Fare Option: PREMIUM (5%)")
    elif fare_option == "FLEXIBLE":
        discount += 10
        reasons.append("Fare Option: FLEXIBLE (10%)")
    elif fare_option == "BUSINESS":
        discount += 15
        reasons.append("Fare Option: BUSINESS (15%)")

    if fare_basis:
        fare_basis = fare_basis.upper()
        if fare_basis.startswith(("NO", "SU", "UL", "LX")):
            discount += 7
            reasons.append(f"Fare Basis: {fare_basis} (7%)")

    if fare_types:
        fare_types = [f.upper() for f in fare_types]
        for ftype in fare_types:
            if ftype in ["SPANISH_RESIDENT", "AIR_FRANCE_DOMESTIC", "AIR_FRANCE_COMBINED", "AIR_FRANCE_METROPOLITAN"]:
                discount += 5
                reasons.append(f"Fare Type: {ftype} (5%)")

    discounted_price = price_inr - (price_inr * discount / 100)
    print(f"Applied Discounts: {', '.join(reasons) if reasons else 'No discounts applied'}")
    return round(discounted_price, 2)


# ====================== BOOK FLIGHT VIEW ======================
def book_flight(request, offer_id):
    try:
        flight_offer = FlightOfferModel.objects.get(id=offer_id)
    except FlightOfferModel.DoesNotExist:
        return render(request, "error.html", {"error": "Invalid Flight Offer"})

    offer_json = flight_offer.offer_json

    fare_option = (
        request.POST.get("fare_option") or 
        request.GET.get("fare_option") or 
        "STANDARD"
    ).upper()

    original_price = float(flight_offer.price_total)
    original_currency = getattr(flight_offer, "currency", "EUR")
    converted_price_inr, _ = convert_to_inr(original_price, from_currency=original_currency)

    # Extract fare basis & types
    fare_basis = None
    fare_types = []
    try:
        details = offer_json.get("travelerPricings", [])[0].get("fareDetailsBySegment", [])
        if details:
            fare_basis = details[0].get("fareBasis")
        fare_types = offer_json.get("pricingOptions", {}).get("fareType", [])
    except:
        pass

    # Apply discount
    final_price_inr = apply_discount(converted_price_inr, fare_option, fare_basis, fare_types)

    # Process itineraries for stops
    for itinerary in offer_json.get("itineraries", []):
        segments = itinerary.get("segments", [])
        itinerary["total_stops"] = max(len(segments) - 1, 0)

    context = {
        "offer_id": offer_id,
        "original_price": f"{original_price} {original_currency}",
        "price_inr": converted_price_inr,
        "final_price_inr": final_price_inr,
        "fare_option": fare_option,
        "fare_basis": fare_basis,
        "fare_types": fare_types,
        "flight": offer_json,
    }

    return render(request, "book_flights.html", context)


# ====================== CREATE FLIGHT ORDER (Amadeus) ======================
def create_flight_order(flight_offer, traveler_info, frequent_flyer_info=None, fare_option="STANDARD"):
    """
    Creates booking via Amadeus API or mock fallback.
    """
    # Prepare loyalty programs only if provided
    loyalty_programs = []
    if frequent_flyer_info:
        loyalty_programs = [{
            "programOwner": frequent_flyer_info.get("program_owner"),
            "accountNumber": frequent_flyer_info.get("account_number"),
        }]

    try:
        travelers = [{
            "id": "1",
            "dateOfBirth": traveler_info.get("dob"),
            "name": {
                "firstName": traveler_info.get("first_name"),
                "lastName": traveler_info.get("last_name"),
            },
            "gender": "MALE",
            "contact": {
                "emailAddress": traveler_info.get("email"),
                "phones": [{
                    "deviceType": "MOBILE",
                    "countryCallingCode": traveler_info.get("country_code", "91"),
                    "number": traveler_info.get("phone"),
                }],
            },
            "fareOptions": [fare_option],
            "loyaltyPrograms": loyalty_programs,
        }]

        offer_data = getattr(flight_offer, "offer_json", {
            "type": "flight-offer",
            "id": str(flight_offer.id),
            "price": {
                "total": str(flight_offer.price_total),
                "currency": "INR",
            },
        })

        if isinstance(offer_data, str):
            offer_data = json.loads(offer_data)

        # Call Amadeus booking API
        response = amadeus.booking.flight_orders.post([offer_data], travelers)
        return True, response.data

    except ResponseError as e:
        if "[400]" in str(e):
            # Mock fallback for testing
            return True, {
                "status": "BOOKED",
                "flight_id": str(flight_offer.id),
                "price": f"{flight_offer.price_total} INR",
                "fare_option": fare_option,
                "traveler": f"{traveler_info.get('first_name')} {traveler_info.get('last_name')}",
                "message": "Mock booking confirmed (Amadeus API 400 fallback)",
            }
        return False, {"error": str(e)}


# ====================== TRAVELER FORM + PAYU PAYMENT ======================
from django.shortcuts import render
from django.conf import settings
import uuid

from routes.models import FlightOfferModel
from airports.views import convert_to_inr

from .models import TravelerDetail, FlightBookingModel
from payment.utils import generate_payu_hash   # ← Yeh line important hai


def traveler_form_view(request, offer_id):
    print("---- traveler_form_view START ----")

    try:
        flight_offer = FlightOfferModel.objects.get(id=offer_id)
        print("✅ Flight Offer Found:", flight_offer.id)
    except FlightOfferModel.DoesNotExist:
        return render(request, "error.html", {"error": "Flight offer not found"})

    try:
        base_price_inr, _ = convert_to_inr(
            float(flight_offer.price_total),
            from_currency=getattr(flight_offer, 'currency', 'EUR')
        )
        print("✅ Base Price INR:", base_price_inr)
    except Exception as e:
        print("❌ Price Conversion Error:", str(e))
        return render(request, "error.html", {"error": "Price conversion failed"})

    if request.method == "POST":
        print("---- POST REQUEST RECEIVED ----")
        print("POST DATA:", request.POST)

        # ================= Traveler Creation =================
        try:
            traveler = TravelerDetail.objects.create(
                first_name=request.POST.get("first_name"),
                last_name=request.POST.get("last_name"),
                dob=request.POST.get("dob"),
                email=request.POST.get("email"),
                phone=request.POST.get("phone"),
                passport_no=request.POST.get("passport_no"),
                passport_expiry=request.POST.get("passport_expiry"),
            )
            print("✅ Traveler Created:", traveler.id)

        except Exception as e:
            print("❌ Traveler Creation Error:", str(e))
            return render(request, "error.html", {"error": str(e)})

        # ================= Extras & Final Price =================
        try:
            extras_selected = []
            total_extras_inr = 0

            possible_extras = [
                ("In-flight Meal", 800, "meal"),
                ("Extra Baggage (23kg)", 2500, "extra_bag"),
                ("Priority Boarding", 600, "priority"),
                ("Preferred Seat", 900, "seat"),
            ]

            for name, price, key in possible_extras:
                if request.POST.get(key) == "on":
                    extras_selected.append({"name": name, "price": price})
                    total_extras_inr += price

            final_price_inr = round(base_price_inr + total_extras_inr, 2)

            # ✅ IMPORTANT FIX: amount format
            amount = "%.2f" % final_price_inr

            print("✅ Extras Total:", total_extras_inr)
            print("✅ Final Price:", final_price_inr)
            print("✅ Formatted Amount:", amount)

        except Exception as e:
            print("❌ Extras/Price Error:", str(e))
            return render(request, "error.html", {"error": str(e)})

        # ================= PayU Payload =================
        try:
            txnid = str(uuid.uuid4()).replace("-", "")[:40]
            print("✅ TXN ID:", txnid)

            # ✅ ONLY DATA FOR HASH
            payu_data = {
                "txnid": txnid,
                "amount": amount,
                "productinfo": f"FlightBooking{offer_id}",
                "firstname": traveler.first_name,
                "email": traveler.email,
                "udf1": str(offer_id),
                "udf2": str(traveler.id),
                "udf3": "",
                "udf4": "",
                "udf5": "",
            }

            # ✅ HASH GENERATE (IMPORTANT)
            payu_hash = generate_payu_hash(payu_data)

            print("✅ HASH GENERATED")

            # ✅ FINAL PAYLOAD (THIS GOES TO HTML)
            payu_payload = {
                "key": settings.PAYU_MERCHANT_KEY,
                "txnid": txnid,
                "amount": amount,
                "productinfo": f"FlightBooking{offer_id}",
                "firstname": traveler.first_name,
                "lastname": traveler.last_name or "",
                "email": traveler.email,
                "phone": traveler.phone,
                "surl": settings.PAYU_SUCCESS_URL,
                "furl": settings.PAYU_FAILURE_URL,
                "udf1": str(offer_id),
                "udf2": str(traveler.id),
                "udf3": "",
                "udf4": "",
                "udf5": "",
                "hash": payu_hash,
            }

            print("✅ PayU Payload Prepared")

        except Exception as e:
            print("❌ PayU Preparation Error:", str(e))
            return render(request, "error.html", {"error": str(e)})

        # ================= Create Booking =================
        try:
            booking = FlightBookingModel.objects.create(
                traveler=traveler,
                flight_offer=flight_offer,
                final_price_inr=final_price_inr,
                booking_status="PENDING",
                payu_txnid=txnid,
                selected_extras=extras_selected,
                extras_amount_inr=total_extras_inr,
            )
            print("✅ Booking Created:", booking.id)

        except Exception as e:
            print("❌ Booking Creation Error:", str(e))
            return render(request, "error.html", {"error": str(e)})

        print("---- REDIRECTING TO PAYMENT PAGE ----")

        return render(request, "payu_redirect.html", {
            "payu_data": payu_payload,
            "action_url": settings.PAYU_URL,
        })

    # ================= GET =================
    return render(request, "traveler_form.html", {
        "flight_offer": flight_offer,
        "base_price_inr": base_price_inr,
    })
