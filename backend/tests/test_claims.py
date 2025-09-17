import os
import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from unittest.mock import patch, MagicMock
import asyncio

from claims.app import app
from claims.db import get_db

TEST_DB_NAME = "uhg_claims_test"


@pytest.fixture(autouse=True, scope="function")
async def setup_test_db():
    # Use test DB; assumes MONGODB_URI points to a local or Atlas test cluster
    os.environ["DB_NAME"] = TEST_DB_NAME

    client = AsyncIOMotorClient(
        os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
        serverSelectionTimeoutMS=5000,
    )
    db = client[TEST_DB_NAME]

    async def _override_db():
        return db

    app.dependency_overrides[get_db] = _override_db

    yield

    try:
        await db.drop_collection("claims")
    except Exception:
        pass

    try:
        client.close()
    except Exception:
        pass

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
        r = await ac.patch(
            f"/claims/{claim_id}", json={"amount_paid": 80.0, "status": "paid"}
        )
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


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_claim_with_all_fields():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "diagnosis_codes": ["E11.9", "Z51.11"],
            "procedure_codes": ["99213", "99214"],
            "amount_billed": 150.0,
            "amount_allowed": 120.0,
            "amount_paid": 100.0,
            "status": "pending",
            "notes": "Test claim with all fields",
        }
        r = await ac.post("/claims", json=payload)
        assert r.status_code == 201
        created = r.json()
        assert ObjectId.is_valid(created["id"]) is True
        assert created["member_id"] == "M1"
        assert created["status"] == "pending"
        assert created["notes"] == "Test claim with all fields"
        assert len(created["diagnosis_codes"]) == 2
        assert len(created["procedure_codes"]) == 2


@pytest.mark.asyncio
async def test_create_claim_minimal_fields():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "member_id": "M2",
            "provider_id": "P2",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 75.0,
        }
        r = await ac.post("/claims", json=payload)
        assert r.status_code == 201
        created = r.json()
        assert created["status"] == "submitted"
        assert created["amount_allowed"] == 0
        assert created["amount_paid"] == 0
        assert created["diagnosis_codes"] == []
        assert created["procedure_codes"] == []


@pytest.mark.asyncio
async def test_get_claim_not_found():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        fake_id = str(ObjectId())
        r = await ac.get(f"/claims/{fake_id}")
        assert r.status_code == 404
        assert r.json()["detail"] == "Claim not found"


@pytest.mark.asyncio
async def test_get_claim_invalid_id():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/claims/invalid_id")
        assert r.status_code == 400
        assert r.json()["detail"] == "Invalid id"


@pytest.mark.asyncio
async def test_update_claim_not_found():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        fake_id = str(ObjectId())
        r = await ac.patch(f"/claims/{fake_id}", json={"status": "paid"})
        assert r.status_code == 404
        assert r.json()["detail"] == "Claim not found"


@pytest.mark.asyncio
async def test_update_claim_invalid_id():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.patch("/claims/invalid_id", json={"status": "paid"})
        assert r.status_code == 400
        assert r.json()["detail"] == "Invalid id"


@pytest.mark.asyncio
async def test_update_claim_no_changes():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
        }
        r = await ac.post("/claims", json=payload)
        claim_id = r.json()["id"]

        r = await ac.patch(f"/claims/{claim_id}", json={})
        assert r.status_code == 200
        assert r.json()["id"] == claim_id


@pytest.mark.asyncio
async def test_delete_claim_not_found():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        fake_id = str(ObjectId())
        r = await ac.delete(f"/claims/{fake_id}")
        assert r.status_code == 404
        assert r.json()["detail"] == "Claim not found"


@pytest.mark.asyncio
async def test_delete_claim_invalid_id():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.delete("/claims/invalid_id")
        assert r.status_code == 400
        assert r.json()["detail"] == "Invalid id"


@pytest.mark.asyncio
async def test_list_claims_empty():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/claims")
        assert r.status_code == 200
        assert r.json() == []


@pytest.mark.asyncio
async def test_list_claims_multiple():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload1 = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
        }
        payload2 = {
            "member_id": "M2",
            "provider_id": "P2",
            "service_date": "2025-09-03",
            "received_date": "2025-09-04",
            "amount_billed": 200.0,
        }

        r1 = await ac.post("/claims", json=payload1)
        r2 = await ac.post("/claims", json=payload2)

        r = await ac.get("/claims")
        assert r.status_code == 200
        claims = r.json()
        assert len(claims) == 2
        claim_ids = [c["id"] for c in claims]
        assert r1.json()["id"] in claim_ids
        assert r2.json()["id"] in claim_ids


@pytest.mark.asyncio
@patch("claims.app.httpx.AsyncClient")
async def test_claim_status_change_triggers_notification(mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True, "notificationId": "test123"}
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    async with AsyncClient(app=app, base_url="http://test") as ac:
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
        assert r.status_code == 201
        claim_id = r.json()["id"]

        r = await ac.patch(
            f"/claims/{claim_id}", json={"status": "paid", "amount_paid": 80.0}
        )
        assert r.status_code == 200

        await asyncio.sleep(0.1)

        mock_client_instance.post.assert_called_once()
        call_args = mock_client_instance.post.call_args
        assert "http://localhost:8000/notify" in call_args[0][0]

        call_json = call_args[1]["json"]
        assert call_json["title"] == "🏥 Healthcare Claim Update"
        assert "approved and payment processed" in call_json["body"]
        assert call_json["member_id"] == "M1"


@pytest.mark.asyncio
@patch("claims.app.httpx.AsyncClient")
async def test_claim_status_change_different_statuses(mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True, "notificationId": "test123"}
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
        }
        r = await ac.post("/claims", json=payload)
        claim_id = r.json()["id"]

        test_cases = [
            ("adjudicated", "reviewed and adjudicated"),
            ("denied", "reviewed. Please contact us"),
            ("pending", "currently under review"),
        ]

        for status, expected_text in test_cases:
            mock_client_instance.reset_mock()

            r = await ac.patch(f"/claims/{claim_id}", json={"status": status})
            assert r.status_code == 200

            await asyncio.sleep(0.1)

            mock_client_instance.post.assert_called_once()
            call_json = mock_client_instance.post.call_args[1]["json"]
            assert expected_text in call_json["body"]


@pytest.mark.asyncio
@patch("claims.app.httpx.AsyncClient")
async def test_claim_status_change_with_notes(mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True, "notificationId": "test123"}
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
        }
        r = await ac.post("/claims", json=payload)
        claim_id = r.json()["id"]

        r = await ac.patch(
            f"/claims/{claim_id}",
            json={"status": "paid", "notes": "Additional documentation required"},
        )
        assert r.status_code == 200

        await asyncio.sleep(0.1)

        mock_client_instance.post.assert_called_once()
        call_json = mock_client_instance.post.call_args[1]["json"]
        assert "Note: Additional documentation required" in call_json["body"]


@pytest.mark.asyncio
@patch("claims.app.httpx.AsyncClient")
async def test_claim_status_no_change_no_notification(mock_httpx_client):
    async with AsyncClient(app=app, base_url="http://test") as ac:
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
        assert r.status_code == 201
        claim_id = r.json()["id"]

        r = await ac.patch(f"/claims/{claim_id}", json={"amount_paid": 80.0})
        assert r.status_code == 200

        await asyncio.sleep(0.1)

        mock_httpx_client.assert_not_called()


@pytest.mark.asyncio
@patch("claims.app.httpx.AsyncClient")
async def test_claim_no_member_id_no_notification(mock_httpx_client):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
        }
        r = await ac.post("/claims", json=payload)
        claim_id = r.json()["id"]

        r = await ac.patch(
            f"/claims/{claim_id}", json={"member_id": None, "status": "paid"}
        )
        assert r.status_code == 200

        await asyncio.sleep(0.1)

        mock_httpx_client.assert_not_called()


@pytest.mark.asyncio
@patch("claims.app.httpx.AsyncClient")
async def test_notification_service_failure_handling(mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    async with AsyncClient(app=app, base_url="http://test") as ac:
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
        assert r.status_code == 201
        claim_id = r.json()["id"]

        r = await ac.patch(
            f"/claims/{claim_id}", json={"status": "paid", "amount_paid": 80.0}
        )
        assert r.status_code == 200
        assert r.json()["status"] == "paid"

        await asyncio.sleep(0.1)

        mock_client_instance.post.assert_called_once()


@pytest.mark.asyncio
@patch("claims.app.httpx.AsyncClient")
async def test_notification_service_timeout_handling(mock_httpx_client):
    import httpx

    mock_client_instance = MagicMock()
    mock_client_instance.post.side_effect = httpx.TimeoutException("Request timeout")
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
        }
        r = await ac.post("/claims", json=payload)
        claim_id = r.json()["id"]

        r = await ac.patch(
            f"/claims/{claim_id}", json={"status": "paid", "amount_paid": 80.0}
        )
        assert r.status_code == 200
        assert r.json()["status"] == "paid"

        await asyncio.sleep(0.1)

        mock_client_instance.post.assert_called_once()


@pytest.mark.asyncio
async def test_claim_status_enum_values():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
        }
        r = await ac.post("/claims", json=payload)
        claim_id = r.json()["id"]

        valid_statuses = ["submitted", "pending", "adjudicated", "paid", "denied"]

        for status in valid_statuses:
            r = await ac.patch(f"/claims/{claim_id}", json={"status": status})
            assert r.status_code == 200
            assert r.json()["status"] == status


@pytest.mark.asyncio
async def test_claim_amount_validation():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
        }
        r = await ac.post("/claims", json=payload)
        claim_id = r.json()["id"]

        r = await ac.patch(
            f"/claims/{claim_id}", json={"amount_allowed": 90.0, "amount_paid": 85.0}
        )
        assert r.status_code == 200
        updated = r.json()
        assert updated["amount_allowed"] == 90.0
        assert updated["amount_paid"] == 85.0
