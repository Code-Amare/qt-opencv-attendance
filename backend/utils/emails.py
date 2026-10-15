from django.template.loader import render_to_string
from django.conf import settings
from utils.send_mail import send_email

def send_verification_code_email(user, code):
    html_content = render_to_string(
        "templates/users/verify_email.html",
        {
            "user": user,
            "code": code,
        },
    )

    send_email(
        to_email=user.email,
        subject="Verify your email address",
        html_content=html_content,
    )

def send_forgot_password_email(user, code):
    html_content = render_to_string(
        "users/forgot_password.html",
        {
            "user": user,
            "code": code,
        }
    )

    send_email(
        to_email=user.email,
        subject="Reset Your Password",
        html_content=html_content,
    )


def send_verification_code_email(user, code):
    html_content = render_to_string(
        "users/verify_email.html",
        {
            "user": user,
            "code": code,
        },
    )

    send_email(
        to_email=user.email,
        subject="Verify your email address",
        html_content=html_content,
    )


def send_login_link_email(user, code):

    html_content = render_to_string(
        "users/login_link.html",
        {
            "user": user,
            "url": f"{settings.FRONTEND_URL}/login/email/verify/{code}/",
        },
    )

    send_email(
        to_email=user.email,
        subject="Your secure login link",
        html_content=html_content,
    )

def send_contact_admin_email(name, email, subject, message):
    html_content = render_to_string(
        "users/contact_admin.html",
        {"name": name, "email": email, "subject": subject, "message": message},
    )

    send_email(
        to_email=settings.CONTACT_RECEIVER_EMAIL,
        subject=f"[Contact] {subject}",
        html_content=html_content,
    )