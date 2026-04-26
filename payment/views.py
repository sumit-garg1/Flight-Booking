import uuid
import random
import string

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User

from payment.utils import send_account_email
from book_flight.models import FlightBookingModel


@csrf_exempt
def payment_success(request):
    """
    PayU Success Handler
    Creates user (if needed)
    Sends booking email always
    """

    print("==== PAYMENT SUCCESS HIT ====")
    print("Method:", request.method)

    booking=None
    message="Payment successful!"
    txnid=None


    if request.method=="POST":

        post_data=request.POST.dict()

        print(
            "POST DATA:",
            post_data
        )

        txnid=post_data.get(
            "txnid"
        )

        status=post_data.get(
            "status",""
        ).lower()


        if txnid:

            booking=(
                FlightBookingModel.objects
                .filter(
                    payu_txnid=txnid
                )
                .first()
            )

            if booking:

                # -------- update payment info --------

                booking.payu_status=post_data.get(
                    "status"
                )

                booking.payu_response=post_data

                booking.payment_verified=True


                if status=="success":

                    booking.booking_status="BOOKED"


                    if not booking.pnr:
                        booking.pnr=(
                            str(uuid.uuid4())[:8]
                            .upper()
                        )


                    # -------- User logic --------

                    email=post_data.get(
                        "email"
                    )

                    first_name=post_data.get(
                        "firstname",""
                    )

                    if email:

                        user=User.objects.filter(
                            username=email
                        ).first()


                        # absolute url dynamic
                        domain=(
                           request.build_absolute_uri('/')
                           [:-1]
                        )


                        # ===== New User =====
                        if not user:

                            password=''.join(
                                random.choices(
                                    string.ascii_letters
                                    + string.digits,
                                    k=8
                                )
                            )

                            user=User.objects.create_user(
                                username=email,
                                email=email,
                                password=password,
                                first_name=first_name
                            )

                            print(
                              f"New user created {email}"
                            )


                            # send account+booking email
                            send_account_email(
                                email=email,
                                first_name=first_name,
                                booking_id=booking.pnr,
                                password=password,
                                account_created=True,
                                domain=domain
                            )


                        # ===== Existing User =====
                        else:

                            print(
                               f"Existing user {email}"
                            )


                            # booking confirmation mail
                            send_account_email(
                                email=email,
                                first_name=first_name,
                                booking_id=booking.pnr,
                                account_created=False,
                                domain=domain
                            )


                        # link booking with user
                        if hasattr(
                            booking,
                            "user"
                        ):
                            booking.user=user


                    message=(
                      "Your flight has been "
                      "successfully booked!"
                    )


                else:

                    booking.booking_status="FAILED"

                    message=(
                      "Payment completed "
                      "but status not success."
                    )


                booking.save()

                print(
                   f"Booking {booking.id} updated"
                )


            else:

                message=(
                    "Booking record "
                    "not found."
                )

                print(
                  "Booking not found for",
                  txnid
                )


    else:
        # Handle GET refresh
        booking=(
            FlightBookingModel.objects
            .filter(
                booking_status="BOOKED"
            )
            .order_by("-id")
            .first()
        )

        if booking:
            message=(
              "Your flight has been "
              "successfully booked!"
            )


    context={
        "booking":booking,
        "message":message,
        "txnid":txnid
    }

    return render(
        request,
        "payment_success.html",
        context
    )



@csrf_exempt
def payment_failure(request):

    print(
       "==== PAYMENT FAILURE HIT ===="
    )

    print(
       "Method:",
       request.method
    )


    if request.method=="POST":

        post_data=request.POST.dict()

        print(
          "Failure Data:",
          post_data
        )

        txnid=post_data.get(
            "txnid"
        )


        if txnid:

            try:

                booking=(
                    FlightBookingModel.objects
                    .filter(
                        payu_txnid=txnid
                    )
                    .first()
                )


                if booking:

                    booking.booking_status="FAILED"

                    booking.payu_status=post_data.get(
                        "status",
                        "failure"
                    )

                    booking.payu_response=post_data

                    booking.payment_verified=False

                    booking.save()

                    print(
                        f"Booking {booking.id} failed"
                    )

            except Exception as e:

                print(
                    "Failure update error:",
                    str(e)
                )


    return render(
        request,
        "payment_failed.html",
        {
            "error":
            "Payment failed or cancelled. "
            "Please try again."
        }
    )