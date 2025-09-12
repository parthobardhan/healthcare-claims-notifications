import os
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .db import get_db, close_db
from .models import User, PushSubscription, NotificationCreate, NotificationRecord, DeliveryRecord
from .notify import send_web_push, get_vapid

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

app = FastAPI(title="Web Notification Service (Integrated)")

origins = os.getenv("CORS_ORIGINS", "http://localhost:4300,http://127.0.0.1:4300,http://localhost:4400,http://127.0.0.1:4400,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000").split(",")
origin_pattern = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_pattern,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Health(BaseModel):
    status: str


@app.get("/health", response_model=Health)
async def health():
    return {"status": "ok"}


@app.on_event("shutdown")
async def shutdown_event():
    await close_db()


@app.get("/vapid-public-key")
async def vapid_public_key():
    return {"publicKey": get_vapid()["publicKey"]}


@app.post("/subscribe")
async def subscribe(sub: PushSubscription, db: AsyncIOMotorDatabase = Depends(get_db), email: Optional[str] = None):
    user_query = {"email": email} if email else {"email": None}
    user = await db.users.find_one(user_query)
    if not user:
        user_doc = {"email": email, "subscriptions": [sub.model_dump(mode="json")]}
        res = await db.users.insert_one(user_doc)
        user_id = str(res.inserted_id)
    else:
        existing = next((s for s in user.get("subscriptions", []) if s.get("endpoint") == sub.endpoint), None)
        if not existing:
            await db.users.update_one(user_query, {"$push": {"subscriptions": sub.model_dump(mode="json")}})
        user_id = str(user["_id"])
    return {"ok": True, "userId": user_id}


@app.post("/notify")
async def notify(payload: NotificationCreate, db: AsyncIOMotorDatabase = Depends(get_db), user_id: Optional[str] = None):
    record = payload.model_dump()
    record.update({"audience": "user" if user_id else "all", "user_id": user_id})
    rec_res = await db.notifications.insert_one(record)

    cursor = None
    if user_id:
        try:
            cursor = db.users.find({"_id": ObjectId(user_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid user_id")
    else:
        cursor = db.users.find({})

    removed = []
    async for user in cursor:
        subs = user.get("subscriptions", [])
        for s in list(subs):
            try:
                send_web_push(s, {
                    "title": payload.title,
                    "body": payload.body,
                    "icon": payload.icon,
                    "url": payload.url,
                })
                await db.deliveries.insert_one({
                    "notification_id": str(rec_res.inserted_id),
                    "user_id": str(user["_id"]),
                    "endpoint": s.get("endpoint"),
                    "status": "sent",
                    "created_at": __import__("datetime").datetime.utcnow().isoformat()
                })
            except Exception as ex:
                resp = getattr(ex, "response", None)
                status = getattr(resp, "status_code", None)
                body_text = ""
                if resp is not None:
                    try:
                        body_text = getattr(resp, "text", "") or ""
                    except Exception:
                        body_text = str(getattr(resp, "body", "") or "")
                if status in (404, 410) or (status == 400 and "VapidPkHashMismatch" in str(body_text)):
                    removed.append(s.get("endpoint"))
                    await db.users.update_one({"_id": user["_id"]}, {"$pull": {"subscriptions": {"endpoint": s.get("endpoint")}}})
                    await db.deliveries.insert_one({
                        "notification_id": str(rec_res.inserted_id),
                        "user_id": str(user["_id"]),
                        "endpoint": s.get("endpoint"),
                        "status": "removed",
                        "status_code": status,
                        "error": str(ex),
                        "created_at": __import__("datetime").datetime.utcnow().isoformat()
                    })
                else:
                    print(f"Web push failed for endpoint {s.get('endpoint')}: {ex}")
                    await db.deliveries.insert_one({
                        "notification_id": str(rec_res.inserted_id),
                        "user_id": str(user.get("_id")),
                        "endpoint": s.get("endpoint"),
                        "status": "failed",
                        "status_code": status,
                        "error": str(ex),
                        "created_at": __import__("datetime").datetime.utcnow().isoformat()
                    })

    return {"ok": True, "notificationId": str(rec_res.inserted_id), "removed": removed}


@app.get("/users", response_model=List[User])
async def list_users(db: AsyncIOMotorDatabase = Depends(get_db)):
    out: List[User] = []
    async for doc in db.users.find({}).limit(100):
        doc["_id"] = str(doc["_id"])  # Convert ObjectId to str for response
        out.append(User.model_validate(doc))
    return out


@app.get("/notifications", response_model=List[NotificationRecord])
async def list_notifications(db: AsyncIOMotorDatabase = Depends(get_db)):
    out: List[NotificationRecord] = []
    async for doc in db.notifications.find({}).sort("_id", -1).limit(100):
        doc["_id"] = str(doc["_id"])  # Convert ObjectId to str for response
        out.append(NotificationRecord.model_validate(doc))
    return out


@app.get("/deliveries", response_model=List[DeliveryRecord])
async def list_deliveries(db: AsyncIOMotorDatabase = Depends(get_db)):
    out: List[DeliveryRecord] = []
    async for doc in db.deliveries.find({}).sort("_id", -1).limit(200):
        doc["_id"] = str(doc["_id"])  # Convert ObjectId to str for response
        out.append(DeliveryRecord.model_validate(doc))
    return out

