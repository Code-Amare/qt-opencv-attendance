import logging
from threading import Thread

from django.conf import settings
from sib_api_v3_sdk import ApiClient, Configuration
from sib_api_v3_sdk.api.transactional_emails_api import TransactionalEmailsApi
from sib_api_v3_sdk.models import SendSmtpEmail
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    sender_name: str = settings.DEFAULT_SENDER_NAME,
    sender_email: str = None,
):
    sender_email = sender_email or settings.BREVO_SENDER_EMAIL
    if not sender_email:
        logger.error("Email not sent to %s: BREVO_SENDER_EMAIL is not set", to_email)
        raise ValueError(
            "BREVO_SENDER_EMAIL must be set in environment variables or passed to the function"
        )

    api_key = settings.BREVO_API_KEY
    if not api_key:
        logger.error("Email not sent to %s: BREVO_API_KEY is not set", to_email)
        raise ValueError("BREVO_API_KEY must be set in environment variables")

    def _send():
        logger.info("Sending email | to=%s | subject=%r | sender=%s", to_email, subject, sender_email)
        try:
            configuration = Configuration()
            configuration.api_key["api-key"] = api_key
            api_instance = TransactionalEmailsApi(ApiClient(configuration))

            email = SendSmtpEmail(
                to=[{"email": to_email}],
                sender={"name": sender_name, "email": sender_email},
                subject=subject,
                html_content=html_content,
            )

            response = api_instance.send_transac_email(email)
            logger.info(
                "Email sent | to=%s | subject=%r | message_id=%s",
                to_email,
                subject,
                getattr(response, "message_id", None),
            )
        except ApiException as e:
            logger.error(
                "Brevo API error | to=%s | subject=%r | status=%s | reason=%s | body=%s",
                to_email,
                subject,
                e.status,
                e.reason,
                e.body,
            )
        except Exception:
            logger.exception("Unexpected error while sending email | to=%s | subject=%r", to_email, subject)

    Thread(target=_send, daemon=True).start()