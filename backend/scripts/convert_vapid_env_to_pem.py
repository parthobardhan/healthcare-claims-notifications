#!/usr/bin/env python3
import os
import base64
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
    PublicFormat,
)


def pad(s: str) -> str:
    return s + "=" * ((4 - (len(s) % 4)) % 4)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    dotenv_path = root / ".env"
    if not dotenv_path.exists():
        print(f"ERROR: .env not found at {dotenv_path}")
        return 1
    vals = {}
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

    pub_env = vals.get("VAPID_PUBLIC_KEY")
    priv_env = vals.get("VAPID_PRIVATE_KEY")
    if not priv_env:
        print("ERROR: VAPID_PRIVATE_KEY missing in .env")
        return 2

    try:
        d_bytes = base64.urlsafe_b64decode(pad(priv_env))
    except Exception as e:
        print(f"ERROR: Failed to decode VAPID_PRIVATE_KEY: {e}")
        return 3

    if len(d_bytes) != 32:
        print(f"WARNING: private key length {len(d_bytes)} bytes (expected 32)")

    d_int = int.from_bytes(d_bytes, "big")
    priv = ec.derive_private_key(d_int, ec.SECP256R1())

    notify_dir = root / "notify"
    notify_dir.mkdir(parents=True, exist_ok=True)
    priv_pem = priv.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    (notify_dir / "private_key.pem").write_bytes(priv_pem)

    pub = priv.public_key()
    pub_pem = pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    (notify_dir / "public_key.pem").write_bytes(pub_pem)

    pub_uncompressed = pub.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    pub_b64u = base64.urlsafe_b64encode(pub_uncompressed).rstrip(b"=").decode()

    print("WROTE:", str((notify_dir / "private_key.pem").resolve()))
    print("WROTE:", str((notify_dir / "public_key.pem").resolve()))
    print("Derived publicKey (base64url):", pub_b64u)
    if pub_env and pub_env != pub_b64u:
        print("WARNING: .env VAPID_PUBLIC_KEY does not match derived public key.")
        print("Update .env VAPID_PUBLIC_KEY and re-subscribe from the Patient UI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

