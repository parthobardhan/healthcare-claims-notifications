import os
import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date

from claims.app import app, send_claim_update_notification
from claims.db import get_db
from claims.models import ClaimCreate, ClaimUpdate

TEST_DB_NAME = "uhg_claims_test"


@pytest.fixture(autouse=True)
async def setup_test_db(monkeypatch):
    # Use test DB; assumes MONGODB_URI points to a local or Atlas test cluster
    os.environ["DB_NAME"] = TEST_DB_NAME
    client = AsyncIOMotorClient(
        os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    )
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
async def test_create_claim_validation():
    """Test claim creation with various validation scenarios."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/claims", json={})
        assert r.status_code == 422

        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": -100.0,
        }
        r = await ac.post("/claims", json=payload)
        assert r.status_code == 422

        payload = {
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
        }
        r = await ac.post("/claims", json=payload)
        assert r.status_code == 201
        created = r.json()
        assert created["status"] == "submitted"
        assert created["amount_allowed"] == 0
        assert created["amount_paid"] == 0


@pytest.mark.asyncio
async def test_get_claim_invalid_id():
    """Test getting claim with invalid ObjectId."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/claims/invalid-id")
        assert r.status_code == 400
        assert "Invalid id" in r.json()["detail"]

        fake_id = str(ObjectId())
        r = await ac.get(f"/claims/{fake_id}")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_claim_invalid_id():
    """Test updating claim with invalid ObjectId."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.patch("/claims/invalid-id", json={"status": "paid"})
        assert r.status_code == 400

        fake_id = str(ObjectId())
        r = await ac.patch(f"/claims/{fake_id}", json={"status": "paid"})
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_claim_invalid_id():
    """Test deleting claim with invalid ObjectId."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.delete("/claims/invalid-id")
        assert r.status_code == 400

        fake_id = str(ObjectId())
        r = await ac.delete(f"/claims/{fake_id}")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_claim_no_changes():
    """Test updating claim with no actual changes."""
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
        
        r = await ac.patch(f"/claims/{claim_id}", json={"notes": None})
        assert r.status_code == 200


@pytest.mark.asyncio
@patch("claims.app.send_claim_update_notification")
async def test_update_claim_status_triggers_notification(mock_notification):
    """Test that status changes trigger notifications."""
    mock_notification.return_value = True
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "member_id": "M123",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
            "status": "submitted"
        }
        r = await ac.post("/claims", json=payload)
        claim_id = r.json()["id"]

        r = await ac.patch(f"/claims/{claim_id}", json={"status": "paid"})
        assert r.status_code == 200
        


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_send_claim_update_notification_success(mock_client_class):
    """Test successful notification sending."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"notificationId": "test-123"}
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await send_claim_update_notification("M123", "claim-123", "paid", "Payment processed")
    
    assert result is True
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "http://localhost:8000/notify" in call_args[0]
    
    notification_data = call_args[1]["json"]
    assert notification_data["title"] == "🏥 Healthcare Claim Update"
    assert "approved and payment processed" in notification_data["body"]
    assert notification_data["member_id"] == "M123"


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_send_claim_update_notification_failure(mock_client_class):
    """Test notification sending failure."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await send_claim_update_notification("M123", "claim-123", "paid")
    
    assert result is False
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_send_claim_update_notification_exception(mock_client_class):
    """Test notification sending with exception."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("Network error")
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await send_claim_update_notification("M123", "claim-123", "paid")
    
    assert result is False


@pytest.mark.asyncio
async def test_send_claim_update_notification_status_messages():
    """Test different status messages in notifications."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"notificationId": "test-123"}
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        test_cases = [
            ("adjudicated", "reviewed and adjudicated"),
            ("paid", "approved and payment processed"),
            ("denied", "reviewed. Please contact us"),
            ("pending", "currently under review"),
            ("submitted", "received and is being processed"),
            ("unknown_status", "updated to: unknown_status")
        ]

        for status, expected_text in test_cases:
            await send_claim_update_notification("M123", "claim-123", status)
            call_args = mock_client.post.call_args
            notification_data = call_args[1]["json"]
            assert expected_text in notification_data["body"]


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_oid_function():
    """Test _oid helper function."""
    from claims.app import _oid
    
    valid_id = str(ObjectId())
    result = _oid(valid_id)
    assert isinstance(result, ObjectId)
    assert str(result) == valid_id
    
    with pytest.raises(Exception):  # HTTPException from FastAPI
        _oid("invalid-id")


def test_normalize_for_mongo():
    """Test _normalize_for_mongo helper function."""
    from claims.app import _normalize_for_mongo
    
    test_data = {
        "service_date": date(2025, 9, 1),
        "amount": 100.0,
        "notes": "test"
    }
    
    result = _normalize_for_mongo(test_data)
    assert result["service_date"] == "2025-09-01"
    assert result["amount"] == 100.0
    assert result["notes"] == "test"


def test_claim_models():
    """Test Pydantic models validation."""
    claim_data = {
        "member_id": "M123",
        "provider_id": "P456",
        "service_date": "2025-09-01",
        "received_date": "2025-09-02",
        "amount_billed": 100.0
    }
    
    claim = ClaimCreate(**claim_data)
    assert claim.member_id == "M123"
    assert claim.status == "submitted"  # default value
    assert claim.amount_allowed == 0  # default value
    
    update_data = {"status": "paid", "amount_paid": 80.0}
    update = ClaimUpdate(**update_data)
    assert update.status == "paid"
    assert update.amount_paid == 80.0
    assert update.member_id is None  # not provided
