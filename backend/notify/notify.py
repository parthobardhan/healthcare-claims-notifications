import json
import os
from typing import Dict


def get_vapid() -> Dict[str, str]:
    public_key = os.getenv("VAPID_PUBLIC_KEY")
    private_key = os.getenv("VAPID_PRIVATE_KEY")
    raw_subject = os.getenv("VAPID_SUBJECT") or "mailto:admin@example.com"
    subject = raw_subject.strip().replace("<", "").replace(">", "")
    if not subject.startswith("mailto:"):
        subject = f"mailto:{subject}"
    if not public_key or not private_key:
        # Look for PEMs inside this notify module folder by default
        base_dir = os.path.dirname(__file__)
        priv_pem_path = os.getenv("VAPID_PRIVATE_KEY_PEM", os.path.join(base_dir, "private_key.pem"))
        pub_pem_path = os.getenv("VAPID_PUBLIC_KEY_PEM", os.path.join(base_dir, "public_key.pem"))
        if os.path.isfile(priv_pem_path):
            with open(priv_pem_path, "r") as f:
                private_key = f.read()
        if os.path.isfile(pub_pem_path):
            with open(pub_pem_path, "r") as f:
                public_key = f.read()
    if not public_key or not private_key:
        raise RuntimeError("VAPID keys not set. Add env vars or place PEMs.")
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

