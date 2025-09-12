import json
import os
import base64
from typing import Dict
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def get_vapid() -> Dict[str, str]:
    public_key_env = os.getenv("VAPID_PUBLIC_KEY")
    private_key_env = os.getenv("VAPID_PRIVATE_KEY")
    raw_subject = os.getenv("VAPID_SUBJECT") or "mailto:admin@example.com"
    subject = raw_subject.strip().replace("<", "").replace(">", "")
    if not subject.startswith("mailto:"):
        subject = f"mailto:{subject}"

    base_dir = os.path.dirname(__file__)
    priv_pem_path = os.getenv("VAPID_PRIVATE_KEY_PEM", os.path.join(base_dir, "private_key.pem"))
    pub_pem_path = os.getenv("VAPID_PUBLIC_KEY_PEM", os.path.join(base_dir, "public_key.pem"))

    # Determine private key to pass to pywebpush
    # IMPORTANT: pywebpush accepts either a file path or a base64url-encoded RAW/DER string.
    # It does NOT accept PEM content string directly.
    private_key_for_pywebpush: str | None = None
    if private_key_env:
        candidate = private_key_env.strip()
        # If candidate looks like a file path, prefer resolving and using it
        if os.path.isabs(candidate) or candidate.endswith(".pem") or (os.path.sep in candidate):
            path_candidate = candidate if os.path.isabs(candidate) else os.path.join(base_dir, candidate)
            if os.path.isfile(path_candidate):
                private_key_for_pywebpush = path_candidate
        if private_key_for_pywebpush is None:
            if "BEGIN" in candidate:
                # Env contains PEM content; write/refresh the PEM on disk and pass the path
                try:
                    # Support PEMs stored in .env with escaped newlines ("\n")
                    pem_text = candidate.replace("\\n", "\n").strip()
                    # Ensure trailing newline for PEM parsers
                    if not pem_text.endswith("\n"):
                        pem_text += "\n"
                    with open(priv_pem_path, "w", encoding="utf-8") as f:
                        f.write(pem_text)
                    private_key_for_pywebpush = priv_pem_path
                except Exception:
                    private_key_for_pywebpush = None
            else:
                # Assume env is base64url of 32-byte scalar (RAW) or DER; validate minimally
                def _pad(s: str) -> str:
                    return s + "=" * ((4 - (len(s) % 4)) % 4)
                try:
                    decoded = base64.urlsafe_b64decode(_pad(candidate))
                    # Accept only RAW 32-byte scalar. Otherwise fall back to PEM path.
                    if len(decoded) == 32:
                        private_key_for_pywebpush = candidate
                except Exception:
                    private_key_for_pywebpush = None
    if private_key_for_pywebpush is None and os.path.isfile(priv_pem_path):
        # Fall back to PEM file path
        private_key_for_pywebpush = priv_pem_path

    # Determine public key to send to browser (applicationServerKey, base64url)
    public_key_for_frontend: str | None = None
    if public_key_env and "BEGIN" not in public_key_env:
        public_key_for_frontend = public_key_env
    else:
        if os.path.isfile(pub_pem_path):
            with open(pub_pem_path, "rb") as f:
                pub = serialization.load_pem_public_key(f.read())
            raw = pub.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
            public_key_for_frontend = _b64url(raw)
        elif os.path.isfile(priv_pem_path):
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            with open(priv_pem_path, "rb") as f:
                prv = load_pem_private_key(f.read(), password=None)
            raw = prv.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
            public_key_for_frontend = _b64url(raw)

    if not public_key_for_frontend or not private_key_for_pywebpush:
        raise RuntimeError("VAPID keys not set. Provide base64url env vars or place PEMs under backend/notify.")

    return {"publicKey": public_key_for_frontend, "privateKey": private_key_for_pywebpush, "subject": subject}


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

