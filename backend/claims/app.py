from typing import List
from datetime import date
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

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
async def create_claim(payload: ClaimCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
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
async def update_claim(claim_id: str, payload: ClaimUpdate, db: AsyncIOMotorDatabase = Depends(get_db)):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        # no-op, just return current doc if exists
        c = await db.claims.find_one({"_id": _oid(claim_id)})
        if not c:
            raise HTTPException(status_code=404, detail="Claim not found")
        c_id = str(c.pop("_id"))
        return ClaimOut(id=c_id, **c)

    # Normalize values (e.g., date -> ISO string) before persisting
    updates = _normalize_for_mongo(updates)

    res = await db.claims.update_one({"_id": _oid(claim_id)}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Claim not found")
    c = await db.claims.find_one({"_id": _oid(claim_id)})
    c_id = str(c.pop("_id"))
    return ClaimOut(id=c_id, **c)


@app.delete("/claims/{claim_id}", status_code=204)
async def delete_claim(claim_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    res = await db.claims.delete_one({"_id": _oid(claim_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Claim not found")
    return None

