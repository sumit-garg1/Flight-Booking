import hashlib
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

def generate_payu_hash(data):
    hash_string = (
        f"{settings.PAYU_MERCHANT_KEY}|{data['txnid']}|{data['amount']}|{data['productinfo']}|"
        f"{data['firstname']}|{data['email']}|{data['udf1']}|{data['udf2']}|||||||||"
        f"{settings.PAYU_MERCHANT_SALT}"
    )

    print("==== FINAL CORRECT HASH ====")
    print("HASH STRING:", hash_string)

    generated_hash = hashlib.sha512(hash_string.encode("utf-8")).hexdigest()

    print("GENERATED HASH:", generated_hash)
    print("============================")

    return generated_hash

def send_account_email(
    email,
    first_name,
    booking_id=None,
    password=None,
    account_created=False,
    domain="https://yourdomain.com",  # change in production
):

    login_url = f"{domain}/login/"
    bookings_url = f"{domain}/my-bookings/"

    subject = "Flight Booking Confirmation ✈"

    # ---------------- TEXT VERSION ---------------- #

    if account_created:
        text_body = f"""
Hello {first_name},

Your flight booking has been confirmed.

Booking ID: {booking_id}

Your account has been created.

Login Email: {email}
Temporary Password: {password}

Login:
{login_url}

Please change your password after login.

Thank you for choosing us.
"""
    else:
        text_body = f"""
Hello {first_name},

Your flight booking has been confirmed.

Booking ID: {booking_id}

Your account already exists.
Use your existing credentials to login:

{login_url}

View bookings:
{bookings_url}

Thank you for choosing us.
"""

    # ---------------- HTML VERSION ---------------- #

    if account_created:
        html_body = f"""
        <html>
        <body>
            <h2>Flight Booking Confirmed ✈</h2>

            <p>Hello <b>{first_name}</b>,</p>

            <p>Your booking has been confirmed.</p>

            <p>
            <b>Booking ID:</b> {booking_id}
            </p>

            <h3>Account Created</h3>

            <p>
            <b>Email:</b> {email}<br>
            <b>Temporary Password:</b> {password}
            </p>

            <p>
            <a href="{login_url}">
                Login to your account
            </a>
            </p>

            <p>Please change your password after first login.</p>

            <p>Thank you for choosing us.</p>
        </body>
        </html>
        """
    else:
        html_body = f"""
        <html>
        <body>
            <h2>Flight Booking Confirmed ✈</h2>

            <p>Hello <b>{first_name}</b>,</p>

            <p>Your booking has been confirmed.</p>

            <p>
            <b>Booking ID:</b> {booking_id}
            </p>

            <p>
            Your account already exists.
            Please login using your existing password.
            </p>

            <p>
            <a href="{login_url}">
                Login
            </a>
            </p>

            <p>
            <a href="{bookings_url}">
                View My Bookings
            </a>
            </p>

            <p>Thank you for choosing us.</p>
        </body>
        </html>
        """

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.EMAIL_HOST_USER,
            to=[email]
        )

        # HTML alternative
        msg.attach_alternative(
            html_body,
            "text/html"
        )

        msg.send()

        return True

    except Exception as e:
        print("Email Error:", str(e))
        return False