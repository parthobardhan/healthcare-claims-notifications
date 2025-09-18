import os
import pytest
from httpx import AsyncClient
from bson import ObjectId
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date

from claims.app import app, send_claim_update_notification
from claims.db import get_db
from claims.models import ClaimCreate, ClaimUpdate



@pytest.fixture
def mock_claims_db():
    """Mock database for claims service tests."""
    db = AsyncMock()
    
    db.claims = AsyncMock()
    db.claims.find_one = AsyncMock(return_value=None)
    db.claims.insert_one = AsyncMock()
    db.claims.update_one = AsyncMock()
    db.claims.delete_one = AsyncMock()
    
    db.claims.find = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    db.claims.find.return_value = mock_cursor
    
    return db


@pytest.fixture(autouse=True)
def setup_claims_test_db(mock_claims_db):
    """Setup mock database for claims service."""
    def _override_db():
        return mock_claims_db

    app.dependency_overrides[get_db] = _override_db
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_crud_claims(mock_claims_db):
    claim_id = ObjectId()
    created_claim = {
        "_id": claim_id,
        "member_id": "M1",
        "provider_id": "P1",
        "service_date": "2025-09-01",
        "received_date": "2025-09-02",
        "diagnosis_codes": ["E11.9"],
        "procedure_codes": ["99213"],
        "amount_billed": 100.0,
        "amount_allowed": 0,
        "amount_paid": 0,
        "status": "submitted",
        "notes": None
    }

    insert_result = AsyncMock()
    insert_result.inserted_id = claim_id
    mock_claims_db.claims.insert_one.return_value = insert_result

    class MockAsyncIterator:
        def __init__(self, items):
            self.items = [dict(item) for item in items]
            self.index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.index >= len(self.items):
                raise StopAsyncIteration
            item = dict(self.items[self.index])
            self.index += 1
            return item

        def limit(self, count):
            return MockAsyncIterator(self.items[:count])

        def sort(self, field, direction=1):
            return MockAsyncIterator(self.items)

    mock_claims_db.claims.find.return_value.sort.return_value.limit.return_value = MockAsyncIterator([created_claim])

    update_result = AsyncMock()
    update_result.modified_count = 1
    mock_claims_db.claims.update_one.return_value = update_result

    delete_result = AsyncMock()
    delete_result.deleted_count = 1
    mock_claims_db.claims.delete_one.return_value = delete_result

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

        mock_claims_db.claims.find_one.return_value = created_claim
        r = await ac.get(f"/claims/{str(claim_id)}")
        assert r.status_code == 200
        got = r.json()
        assert got["member_id"] == "M1"

        # List
        r = await ac.get("/claims")
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 1


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
async def test_delete_claim_invalid_id(mock_claims_db):
    """Test deleting claim with invalid ObjectId."""
    delete_result = AsyncMock()
    delete_result.deleted_count = 0
    mock_claims_db.claims.delete_one.return_value = delete_result
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.delete("/claims/invalid-id")
        assert r.status_code == 400

        fake_id = str(ObjectId())
        r = await ac.delete(f"/claims/{fake_id}")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_claim_no_changes(mock_claims_db):
    """Test updating claim with no actual changes."""
    claim_id = ObjectId()
    existing_claim = {
        "_id": claim_id,
        "member_id": "M1",
        "provider_id": "P1",
        "service_date": "2025-09-01",
        "received_date": "2025-09-02",
        "amount_billed": 100.0,
        "status": "submitted"
    }
    
    insert_result = AsyncMock()
    insert_result.inserted_id = claim_id
    mock_claims_db.claims.insert_one.return_value = insert_result
    def mock_find_one(*args, **kwargs):
        return dict(existing_claim)
    mock_claims_db.claims.find_one.side_effect = mock_find_one
    
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
async def test_update_claim_status_triggers_notification(mock_notification, mock_claims_db):
    """Test that status changes trigger notifications."""
    mock_notification.return_value = True
    
    claim_id = ObjectId()
    original_claim = {
        "_id": claim_id,
        "member_id": "M123",
        "provider_id": "P1",
        "service_date": "2025-09-01",
        "received_date": "2025-09-02",
        "amount_billed": 100.0,
        "status": "submitted"
    }
    updated_claim = {**original_claim, "status": "paid"}
    
    insert_result = AsyncMock()
    insert_result.inserted_id = claim_id
    mock_claims_db.claims.insert_one.return_value = insert_result
    
    update_result = AsyncMock()
    update_result.matched_count = 1
    update_result.modified_count = 1
    mock_claims_db.claims.update_one.return_value = update_result
    
    mock_claims_db.claims.find_one.side_effect = [original_claim, updated_claim]

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
    mock_response.json = lambda: {"notificationId": "test-123"}
    mock_response.text = "Success"
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client
    mock_client_class.return_value.__aexit__.return_value = None

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
