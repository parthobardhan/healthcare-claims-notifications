import os
import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from app.main import app
from app.db import get_db

TEST_DB_NAME = "uhg_claims_test"


@pytest.fixture(autouse=True)
async def setup_test_db(monkeypatch):
    # Use test DB; assumes MONGODB_URI points to a local or Atlas test cluster
    os.environ["DB_NAME"] = TEST_DB_NAME
    client = AsyncIOMotorClient(os.environ.get("MONGODB_URI", "mongodb://localhost:27017"))
    db = client[TEST_DB_NAME]

    async def _override_db():
        return db

    app.dependency_overrides[get_db] = _override_db

    yield

    # Cleanup
    await db.drop_collection("claims")
    client.close()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_crud_claims():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create
        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "diagnosis_codes": ["E11.9"],
            "procedure_codes": ["99213"],
            "amount_billed": 100.0,
        }
        r = await ac.post("/claims", json=payload)
        assert r.status_code == 201, r.text
        created = r.json()
        assert ObjectId.is_valid(created["id"]) is True
        claim_id = created["id"]

        # Get one
        r = await ac.get(f"/claims/{claim_id}")
        assert r.status_code == 200
        got = r.json()
        assert got["member_id"] == "M1"

        # List
        r = await ac.get("/claims")
        assert r.status_code == 200
        items = r.json()
        assert any(i["id"] == claim_id for i in items)

        # Update
        r = await ac.patch(f"/claims/{claim_id}", json={"amount_paid": 80.0, "status": "paid"})
        assert r.status_code == 200
        upd = r.json()
        assert upd["amount_paid"] == 80.0
        assert upd["status"] == "paid"

        # Delete
        r = await ac.delete(f"/claims/{claim_id}")
        assert r.status_code == 204

        # Not found afterwards
        r = await ac.get(f"/claims/{claim_id}")
        assert r.status_code == 404

