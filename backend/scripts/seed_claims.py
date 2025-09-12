import os
import asyncio
import random
import argparse

from datetime import date, timedelta
from typing import List

from motor.motor_asyncio import AsyncIOMotorClient
import sys
from pathlib import Path
# Ensure backend dir (parent of scripts) is on sys.path to import app.*
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# Reuse claims module DB settings
from claims.db import get_mongo_uri, get_db_name
from claims.models import ClaimStatus


DIAG_CODES = ["E11.9", "I10", "J06.9", "M54.5", "K21.9", "N39.0", "E78.5"]
PROC_CODES = ["99213", "93000", "80050", "71020", "90471", "97110", "36415"]


def _iso(d: date) -> str:
    return d.isoformat()


def _make_statuses(n: int) -> List[str]:
    """Return a list of n statuses with exactly 7 pending and the rest distributed
    across submitted, adjudicated, paid, denied.
    """
    assert n >= 7
    remaining = n - 7
    # A reasonable distribution across the others
    # Tune counts but ensure sum == remaining
    base = {"submitted": 3, "adjudicated": 4, "paid": 4, "denied": 2}
    total_base = sum(base.values())
    if total_base != remaining:
        # Scale or adjust if n changes from 20
        other_statuses = ["submitted", "adjudicated", "paid", "denied"]
        base = {s: 0 for s in other_statuses}
        for i in range(remaining):
            base[other_statuses[i % len(other_statuses)]] += 1
    statuses = [ClaimStatus.pending.value] * 7
    for s, cnt in base.items():
        statuses.extend([s] * cnt)
    random.shuffle(statuses)
    return statuses


def _amounts_for_status(status: str, billed: float) -> tuple[float, float]:
    """
    Return (allowed, paid) based on status and billed.
    """
    allowed = round(billed * random.uniform(0.6, 0.9), 2)
    if status == ClaimStatus.paid.value:
        paid = allowed
    elif status == ClaimStatus.denied.value:
        allowed = 0.0
        paid = 0.0
    elif status in (ClaimStatus.pending.value, ClaimStatus.submitted.value):
        paid = 0.0
    elif status == ClaimStatus.adjudicated.value:
        # Some portion of allowed paid
        paid = round(allowed * random.uniform(0.4, 0.9), 2)
    else:
        paid = 0.0
    return allowed, paid


def build_mock_claims(n: int = 20) -> List[dict]:
    random.seed(42)  # reproducible-ish
    today = date.today()
    statuses = _make_statuses(n)
    docs: List[dict] = []

    for i in range(1, n + 1):
        # Dates within last 120 days
        service_dt = today - timedelta(days=random.randint(5, 120))
        received_dt = service_dt + timedelta(days=random.randint(0, 10))

        billed = round(random.uniform(80.0, 1500.0), 2)
        status = statuses[i - 1]
        allowed, paid = _amounts_for_status(status, billed)

        doc = {
            "member_id": f"M{str(i).zfill(3)}",
            "provider_id": f"P{str((i % 15) + 1).zfill(3)}",
            "service_date": _iso(service_dt),
            "received_date": _iso(received_dt),
            "diagnosis_codes": random.sample(DIAG_CODES, k=random.randint(1, 2)),
            "procedure_codes": random.sample(PROC_CODES, k=random.randint(1, 2)),
            "amount_billed": billed,
            "amount_allowed": allowed,
            "amount_paid": paid,
            "status": status,
            "notes": random.choice([
                None,
                "Initial submission",
                "Resubmitted with additional documentation",
                "Requires medical review",
                "Auto-adjudicated",
                "Member responsibility applied",
            ]),
        }
        # Remove None notes to keep field optional
        if doc["notes"] is None:
            doc.pop("notes")
        docs.append(doc)
    return docs


async def main():
    parser = argparse.ArgumentParser(description="Seed mock claims into MongoDB")
    parser.add_argument("--reset", action="store_true", help="Drop the claims collection before seeding")
    parser.add_argument("--count", type=int, default=20, help="Number of claims to insert (>=7)")
    args = parser.parse_args()

    if args.count < 7:
        raise SystemExit("--count must be at least 7 (to allow 7 pending)")

    uri = get_mongo_uri()
    db_name = get_db_name()
    client = AsyncIOMotorClient(uri)
    db = client[db_name]

    if args.reset:
        try:
            await db.drop_collection("claims")
            print("Dropped existing 'claims' collection")
        except Exception as e:
            print(f"Warning: could not drop collection: {e}")

    docs = build_mock_claims(args.count)

    res = await db.claims.insert_many(docs)
    print(f"Inserted {len(res.inserted_ids)} claims into '{db_name}.claims'.")

    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    stats = await db.claims.aggregate(pipeline).to_list(length=None)
    for s in stats:
        print(f"Status={s['_id']}: {s['count']}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())

