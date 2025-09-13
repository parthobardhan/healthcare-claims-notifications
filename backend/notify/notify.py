import json
import os
from typing import Dict


# Simple VAPID key configuration following web-notification-2 pattern
def get_vapid() -> Dict[str, str]:
    """
    Get VAPID keys using the simple, successful pattern from web-notification-2.
    Uses env vars if available, otherwise defaults to hardcoded keys for development.
    """
    # Use environment variables if available, otherwise use healthcare-claims specific keys
    public_key = os.getenv(
        "VAPID_PUBLIC_KEY",
        "BDMDBW7Xk4LErBOYtpIxdROk7gtr40VIY6r_aWYbjwP3l4Nu04yaBfcABCwYS87PO69sXyLJ1l9oHo6RrqkZNRs",
    )
    private_key = os.getenv(
        "VAPID_PRIVATE_KEY", "m9aQf2oTdusZgFIV9JZtEN8aukNQ4zYOD2tcwQIiBjw"
    )
    subject = os.getenv("VAPID_SUBJECT", "mailto:admin@healthcareclaims.com")

    # Ensure subject is properly formatted
    if not subject.startswith("mailto:"):
        subject = f"mailto:{subject}"

    return {"publicKey": public_key, "privateKey": private_key, "subject": subject}


def send_web_push(subscription: Dict, payload: Dict):
    # Lazy import so simple endpoints don't require pywebpush
    from pywebpush import webpush, WebPushException

    vapid = get_vapid()
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=vapid["privateKey"],
            vapid_claims={"sub": vapid["subject"]},
        )
    except WebPushException as ex:
        raise ex
