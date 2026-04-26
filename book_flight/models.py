from django.db import models
from django.contrib.auth.models import User


class TravelerDetail(models.Model):
    first_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    email = models.EmailField(max_length=50, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    passport_no = models.CharField(max_length=40, null=True, blank=True)
    passport_expiry = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()


class FlightBookingModel(models.Model):

    BOOKING_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("BOOKED", "Booked"),
        ("FAILED", "Failed"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("PENDING", "Pending"),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    traveler = models.ForeignKey(
        "TravelerDetail",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    flight_offer = models.ForeignKey(
        "routes.FlightOfferModel",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    fare_option = models.CharField(max_length=20, default="STANDARD", null=True, blank=True)

    # 💰 Pricing
    final_price_inr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # 📌 Booking Info
    booking_status = models.CharField(
        max_length=20,
        choices=BOOKING_STATUS_CHOICES,
        default="PENDING",
        null=True,
        blank=True
    )

    pnr = models.CharField(max_length=30, null=True, blank=True)

    booking_response = models.JSONField(null=True, blank=True)

    # 💳 PayU Fields
    payu_txnid = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payu_mihpayid = models.CharField(max_length=100, null=True, blank=True)

    payu_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="PENDING",
        null=True,
        blank=True
    )

    payu_response = models.JSONField(null=True, blank=True)

    payment_verified = models.BooleanField(default=False)

    # 🎁 Extras
    selected_extras = models.JSONField(default=list, blank=True)
    extras_amount_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)

    # ⏱ Time
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.id} - {self.traveler} - {self.booking_status}"