from typing import List
from datetime import date
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import httpx
import asyncio
import os

from .db import get_db, close_db
from .models import ClaimCreate, ClaimUpdate, ClaimOut

app = FastAPI(title="UHG Claims Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Notification service configuration
NOTIFY_SERVICE_URL = os.getenv("NOTIFY_SERVICE_URL", "http://localhost:8000")


async def send_claim_update_notification(
    member_id: str, claim_id: str, status: str, notes: str = ""
):
    """Send a push notification to the patient when their claim is updated."""
    try:
        # Create notification message
        title = "🏥 Healthcare Claim Update"

        # Customize message based on status
        status_messages = {
            "adjudicated": "Your claim has been reviewed and adjudicated.",
            "paid": "Great news! Your claim has been approved and payment processed.",
            "denied": "Your claim has been reviewed. Please contact us for details.",
            "pending": "Your claim is currently under review.",
            "submitted": "Your claim has been received and is being processed.",
        }

        body = status_messages.get(
            status, f"Your claim status has been updated to: {status}"
        )
        if notes:
            body += f" Note: {notes}"

        # Send notification to the notify service
        notification_data = {
            "title": title,
            "body": body,
            "icon": "/favicon.ico",
            "url": "http://localhost:4201/",
            "member_id": member_id,  # Target specific member
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{NOTIFY_SERVICE_URL}/notify",
                json=notification_data,
                params={"member_id": member_id} if member_id else {},
            )

            if response.status_code == 200:
                result = response.json()
                print(
                    f"✅ Notification sent for claim {claim_id} to member {member_id}: {result.get('notificationId')}"
                )
                return True
            else:
                print(
                    f"❌ Failed to send notification: {response.status_code} {response.text}"
                )
                return False

    except Exception as e:
        print(f"❌ Error sending notification for claim {claim_id}: {str(e)}")
        return False


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("shutdown")
async def shutdown_event():
    await close_db()


def _oid(id: str) -> ObjectId:
    try:
        return ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def _normalize_for_mongo(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, date):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@app.post("/claims", response_model=ClaimOut, status_code=201)
async def create_claim(
    payload: ClaimCreate, db: AsyncIOMotorDatabase = Depends(get_db)
):
    doc = _normalize_for_mongo(payload.model_dump())
    res = await db.claims.insert_one(doc)
    return ClaimOut(id=str(res.inserted_id), **doc)


@app.get("/claims", response_model=List[ClaimOut])
async def list_claims(db: AsyncIOMotorDatabase = Depends(get_db)):
    out: List[ClaimOut] = []
    async for c in db.claims.find({}).sort("_id", -1).limit(200):
        c_id = str(c.pop("_id"))
        out.append(ClaimOut(id=c_id, **c))
    return out


@app.get("/claims/{claim_id}", response_model=ClaimOut)
async def get_claim(claim_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    c = await db.claims.find_one({"_id": _oid(claim_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    c_id = str(c.pop("_id"))
    return ClaimOut(id=c_id, **c)


@app.patch("/claims/{claim_id}", response_model=ClaimOut)
async def update_claim(
    claim_id: str, payload: ClaimUpdate, db: AsyncIOMotorDatabase = Depends(get_db)
):
    # Get original claim first to check for status changes
    original_claim = await db.claims.find_one({"_id": _oid(claim_id)})
    if not original_claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    updates = {
        k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None
    }
    if not updates:
        # no-op, just return current doc if exists
        c_id = str(original_claim.pop("_id"))
        return ClaimOut(id=c_id, **original_claim)

    # Normalize values (e.g., date -> ISO string) before persisting
    updates = _normalize_for_mongo(updates)

    res = await db.claims.update_one({"_id": _oid(claim_id)}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Get updated claim
    updated_claim = await db.claims.find_one({"_id": _oid(claim_id)})
    c_id = str(updated_claim.pop("_id", updated_claim.get("_id")))

    # Check if status changed and send notification
    original_status = original_claim.get("status")
    new_status = updated_claim.get("status")
    member_id = updated_claim.get("member_id")

    if original_status != new_status and member_id:
        print(
            f"🔔 Status changed from {original_status} -> {new_status} for member {member_id}"
        )

        # Send notification asynchronously (don't block the response)
        asyncio.create_task(
            send_claim_update_notification(
                member_id=member_id,
                claim_id=claim_id,
                status=new_status,
                notes=updated_claim.get("notes", ""),
            )
        )

    return ClaimOut(id=c_id, **updated_claim)


@app.delete("/claims/{claim_id}", status_code=204)
async def delete_claim(claim_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    res = await db.claims.delete_one({"_id": _oid(claim_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Claim not found")
    return None
