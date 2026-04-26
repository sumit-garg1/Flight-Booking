from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from book_flight.models import FlightBookingModel
from django.contrib.auth.models import User

from .models import *
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages

# In your profile view, add total_spent calculation
@login_required
def profile(request):
    bookings = FlightBookingModel.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate total spent
    total_spent = sum(float(booking.final_price_inr or 0) for booking in bookings)
    
    context = {
        'user': request.user,
        'bookings': bookings,
        'total_spent': total_spent,
    }
    return render(request, 'profile.html', context)

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect("/")   # home page ya dashboard
        else:
            messages.error(request, "Invalid email or password")

    return render(request, "login.html")

@login_required
def my_bookings_view(request):
    bookings = FlightBookingModel.objects.filter(
        user=request.user
    ).order_by('-id')

    return render(request, "my_bookings.html", {
        "bookings": bookings
    })

def logout_view(request):
    logout(request)
    return redirect("/")

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from book_flight.models import FlightBookingModel

def download_ticket(request, pnr):
    """Download booking ticket as PDF"""
    booking = get_object_or_404(FlightBookingModel, pnr=pnr)
    
    # Create PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # PDF Content
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, 750, "Flight E-Ticket")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, 700, f"Booking PNR: {booking.pnr}")
    p.drawString(50, 680, f"Passenger: {booking.traveler.first_name} {booking.traveler.last_name}")
    p.drawString(50, 660, f"Amount Paid: ₹{booking.final_price_inr}")
    p.drawString(50, 640, f"Status: {booking.booking_status}")
    
    # Add flight details if available
    if booking.flight_offer and booking.flight_offer.offer_json:
        try:
            itineraries = booking.flight_offer.offer_json.get('itineraries', [])
            if itineraries:
                y_position = 600
                p.drawString(50, y_position, "Flight Details:")
                y_position -= 25
                
                for itinerary in itineraries:
                    for segment in itinerary.get('segments', []):
                        p.drawString(70, y_position, f"{segment.get('carrierCode', 'N/A')} {segment.get('number', 'N/A')}")
                        y_position -= 20
                        p.drawString(70, y_position, f"From: {segment.get('departure', {}).get('iataCode', 'N/A')} at {segment.get('departure', {}).get('at', 'N/A')}")
                        y_position -= 20
                        p.drawString(70, y_position, f"To: {segment.get('arrival', {}).get('iataCode', 'N/A')} at {segment.get('arrival', {}).get('at', 'N/A')}")
                        y_position -= 20
                        p.drawString(70, y_position, f"Duration: {segment.get('duration', 'N/A')}")
                        y_position -= 30
        except:
            pass
    
    p.showPage()
    p.save()
    
    # Return PDF
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{booking.pnr}.pdf"'
    return response


def booking_detail(request, pnr):
    """View booking details page"""
    from django.shortcuts import render
    booking = get_object_or_404(FlightBookingModel, pnr=pnr)
    return render(request, 'booking_detail.html', {'booking': booking})