import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from bson import ObjectId
from datetime import date

from claims.app import app, send_claim_update_notification, _oid, _normalize_for_mongo
from claims.db import get_db, get_mongo_uri, get_db_name
from claims.models import ClaimCreate, ClaimUpdate, ClaimOut, ClaimStatus

TEST_DB_NAME = "uhg_claims_test"


@pytest.fixture(autouse=True)
def setup_test_db():
    """Setup test database with proper mocking."""
    from claims.app import app
    from motor.motor_asyncio import AsyncIOMotorDatabase

    mock_db = AsyncMock(spec=AsyncIOMotorDatabase)
    mock_db.claims = AsyncMock()

    mock_db.claims.find_one = AsyncMock(return_value=None)
    mock_db.claims.insert_one = AsyncMock(
        return_value=AsyncMock(inserted_id=ObjectId())
    )
    mock_db.claims.update_one = AsyncMock(return_value=AsyncMock(matched_count=0))
    mock_db.claims.delete_one = AsyncMock(return_value=AsyncMock(deleted_count=0))

    def _override_db():
        return mock_db

    app.dependency_overrides[get_db] = _override_db

    yield mock_db

    app.dependency_overrides.clear()


class TestClaimsAPI:
    """Test cases for the claims API endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health endpoint returns ok status."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_crud_claims(self, setup_test_db):
        mock_db = setup_test_db
        claim_id = ObjectId()

        claim_doc = {
            "_id": claim_id,
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "diagnosis_codes": ["E11.9"],
            "procedure_codes": ["99213"],
            "amount_billed": 100.0,
            "status": "submitted",
        }

        mock_result = AsyncMock()
        mock_result.inserted_id = claim_id
        mock_db.claims.insert_one = AsyncMock(return_value=mock_result)

        mock_db.claims.find_one = AsyncMock(return_value=claim_doc)

        mock_update_result = AsyncMock()
        mock_update_result.matched_count = 1
        mock_db.claims.update_one = AsyncMock(return_value=mock_update_result)

        class MockCursor:
            def __init__(self, data):
                self.data = data

            def sort(self, field, direction):
                return self

            def limit(self, count):
                return self

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.data:
                    doc = self.data.pop(0)
                    if "_id" not in doc:
                        doc["_id"] = claim_id
                    return doc
                raise StopAsyncIteration

        mock_db.claims.find = lambda *args, **kwargs: MockCursor([claim_doc])

        mock_delete_result = AsyncMock()
        mock_delete_result.deleted_count = 1
        mock_db.claims.delete_one = AsyncMock(return_value=mock_delete_result)

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
            claim_id_str = created["id"]

            # Get one
            r = await ac.get(f"/claims/{claim_id_str}")
            assert r.status_code == 200
            got = r.json()
            assert got["member_id"] == "M1"

            # List
            r = await ac.get("/claims")
            assert r.status_code == 200
            items = r.json()
            assert any(i["id"] == claim_id_str for i in items)

            updated_claim_doc = claim_doc.copy()
            updated_claim_doc["amount_paid"] = 80.0
            updated_claim_doc["status"] = "paid"
            mock_db.claims.find_one = AsyncMock(
                side_effect=[claim_doc, updated_claim_doc]
            )

            r = await ac.patch(
                f"/claims/{claim_id_str}", json={"amount_paid": 80.0, "status": "paid"}
            )
            assert r.status_code == 200
            upd = r.json()
            assert upd["amount_paid"] == 80.0
            assert upd["status"] == "paid"

            # Delete
            r = await ac.delete(f"/claims/{claim_id_str}")
            assert r.status_code == 204

            # Not found afterwards - mock not found
            mock_db.claims.find_one = AsyncMock(return_value=None)
            r = await ac.get(f"/claims/{claim_id_str}")
            assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_create_claim_with_all_fields(self):
        """Test creating a claim with all optional fields."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            payload = {
                "member_id": "M123",
                "provider_id": "P456",
                "service_date": "2025-09-01",
                "received_date": "2025-09-02",
                "diagnosis_codes": ["E11.9", "Z51.11"],
                "procedure_codes": ["99213", "99214"],
                "amount_billed": 150.0,
                "amount_allowed": 120.0,
                "amount_paid": 100.0,
                "status": "adjudicated",
                "notes": "Test claim with all fields",
            }
            r = await ac.post("/claims", json=payload)
            assert r.status_code == 201
            created = r.json()
            assert created["member_id"] == "M123"
            assert created["status"] == "adjudicated"
            assert created["notes"] == "Test claim with all fields"
            assert len(created["diagnosis_codes"]) == 2
            assert len(created["procedure_codes"]) == 2

    @pytest.mark.asyncio
    async def test_create_claim_invalid_data(self):
        """Test creating claim with invalid data."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            payload = {
                "member_id": "M1",
            }
            r = await ac.post("/claims", json=payload)
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

    @pytest.mark.asyncio
    async def test_get_claim_not_found(self):
        """Test getting non-existent claim."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            fake_id = str(ObjectId())
            r = await ac.get(f"/claims/{fake_id}")
            assert r.status_code == 404
            assert "Claim not found" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_claim_invalid_id(self):
        """Test getting claim with invalid ID format."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.get("/claims/invalid_id")
            assert r.status_code == 400
            assert "Invalid id" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_claim_not_found(self):
        """Test updating non-existent claim."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            fake_id = str(ObjectId())
            r = await ac.patch(f"/claims/{fake_id}", json={"status": "paid"})
            assert r.status_code == 404
            assert "Claim not found" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_claim_invalid_id(self):
        """Test updating claim with invalid ID format."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.patch("/claims/invalid_id", json={"status": "paid"})
            assert r.status_code == 400
            assert "Invalid id" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_claim_no_changes(self, setup_test_db):
        """Test updating claim with no actual changes."""
        mock_db = setup_test_db
        claim_id = ObjectId()

        claim_doc = {
            "_id": claim_id,
            "member_id": "M1",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
        }

        mock_result = AsyncMock()
        mock_result.inserted_id = claim_id
        mock_db.claims.insert_one = AsyncMock(return_value=mock_result)

        mock_db.claims.find_one = AsyncMock(return_value=claim_doc)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            payload = {
                "member_id": "M1",
                "provider_id": "P1",
                "service_date": "2025-09-01",
                "received_date": "2025-09-02",
                "amount_billed": 100.0,
            }
            r = await ac.post("/claims", json=payload)
            claim_id_str = r.json()["id"]

            r = await ac.patch(f"/claims/{claim_id_str}", json={})
            assert r.status_code == 200
            assert r.json()["member_id"] == "M1"

    @pytest.mark.asyncio
    async def test_update_claim_with_notification(self, setup_test_db):
        """Test updating claim status triggers notification."""
        mock_db = setup_test_db
        claim_id = ObjectId()

        original_claim_doc = {
            "_id": claim_id,
            "member_id": "M123",
            "provider_id": "P1",
            "service_date": "2025-09-01",
            "received_date": "2025-09-02",
            "amount_billed": 100.0,
            "status": "submitted",
        }

        updated_claim_doc = original_claim_doc.copy()
        updated_claim_doc["status"] = "paid"

        mock_result = AsyncMock()
        mock_result.inserted_id = claim_id
        mock_db.claims.insert_one = AsyncMock(return_value=mock_result)

        mock_update_result = AsyncMock()
        mock_update_result.matched_count = 1
        mock_db.claims.update_one = AsyncMock(return_value=mock_update_result)

        mock_db.claims.find_one = AsyncMock(
            side_effect=[original_claim_doc, updated_claim_doc]
        )

        with patch("claims.app.send_claim_update_notification") as mock_notify:
            mock_notify.return_value = True

            async with AsyncClient(app=app, base_url="http://test") as ac:
                payload = {
                    "member_id": "M123",
                    "provider_id": "P1",
                    "service_date": "2025-09-01",
                    "received_date": "2025-09-02",
                    "amount_billed": 100.0,
                    "status": "submitted",
                }
                r = await ac.post("/claims", json=payload)
                claim_id_str = r.json()["id"]

                r = await ac.patch(f"/claims/{claim_id_str}", json={"status": "paid"})
                assert r.status_code == 200
                assert r.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_delete_claim_not_found(self):
        """Test deleting non-existent claim."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            fake_id = str(ObjectId())
            r = await ac.delete(f"/claims/{fake_id}")
            assert r.status_code == 404
            assert "Claim not found" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_claim_invalid_id(self):
        """Test deleting claim with invalid ID format."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.delete("/claims/invalid_id")
            assert r.status_code == 400
            assert "Invalid id" in r.json()["detail"]


class TestClaimsModels:
    """Test cases for Pydantic models validation."""

    def test_claim_create_valid(self):
        """Test valid ClaimCreate model."""
        data = {
            "member_id": "M123",
            "provider_id": "P456",
            "service_date": date(2025, 9, 1),
            "received_date": date(2025, 9, 2),
            "diagnosis_codes": ["E11.9"],
            "procedure_codes": ["99213"],
            "amount_billed": 100.0,
        }
        claim = ClaimCreate(**data)
        assert claim.member_id == "M123"
        assert claim.status == ClaimStatus.submitted
        assert claim.amount_allowed == 0
        assert claim.amount_paid == 0

    def test_claim_create_invalid_amount(self):
        """Test ClaimCreate with invalid negative amount."""
        data = {
            "member_id": "M123",
            "provider_id": "P456",
            "service_date": date(2025, 9, 1),
            "received_date": date(2025, 9, 2),
            "amount_billed": -100.0,
        }
        with pytest.raises(ValueError):
            ClaimCreate(**data)

    def test_claim_update_partial(self):
        """Test ClaimUpdate with partial data."""
        data = {"status": "paid", "amount_paid": 80.0}
        update = ClaimUpdate(**data)
        assert update.status == ClaimStatus.paid
        assert update.amount_paid == 80.0
        assert update.member_id is None

    def test_claim_out_with_id(self):
        """Test ClaimOut model with ID."""
        data = {
            "id": str(ObjectId()),
            "member_id": "M123",
            "provider_id": "P456",
            "service_date": date(2025, 9, 1),
            "received_date": date(2025, 9, 2),
            "amount_billed": 100.0,
        }
        claim = ClaimOut(**data)
        assert ObjectId.is_valid(claim.id)

    def test_claim_status_enum(self):
        """Test ClaimStatus enum values."""
        assert ClaimStatus.submitted == "submitted"
        assert ClaimStatus.pending == "pending"
        assert ClaimStatus.adjudicated == "adjudicated"
        assert ClaimStatus.paid == "paid"
        assert ClaimStatus.denied == "denied"


class TestClaimsUtils:
    """Test cases for utility functions."""

    def test_oid_valid(self):
        """Test _oid with valid ObjectId string."""
        valid_id = str(ObjectId())
        result = _oid(valid_id)
        assert isinstance(result, ObjectId)
        assert str(result) == valid_id

    def test_oid_invalid(self):
        """Test _oid with invalid ObjectId string."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _oid("invalid_id")
        assert exc_info.value.status_code == 400
        assert "Invalid id" in str(exc_info.value.detail)

    def test_normalize_for_mongo_with_date(self):
        """Test _normalize_for_mongo with date objects."""
        data = {
            "service_date": date(2025, 9, 1),
            "amount": 100.0,
            "status": "submitted",
        }
        result = _normalize_for_mongo(data)
        assert result["service_date"] == "2025-09-01"
        assert result["amount"] == 100.0
        assert result["status"] == "submitted"

    def test_normalize_for_mongo_no_dates(self):
        """Test _normalize_for_mongo with no date objects."""
        data = {"amount": 100.0, "status": "submitted"}
        result = _normalize_for_mongo(data)
        assert result == data


class TestClaimsDB:
    """Test cases for database utility functions."""

    def test_get_mongo_uri_default(self):
        """Test get_mongo_uri with default value."""
        with patch.dict("os.environ", {}, clear=True):
            uri = get_mongo_uri()
            assert uri == "mongodb://localhost:27017"

    def test_get_mongo_uri_from_env(self):
        """Test get_mongo_uri from environment variable."""
        test_uri = "mongodb://test:27017"
        with patch.dict("os.environ", {"MONGODB_URI": test_uri}):
            uri = get_mongo_uri()
            assert uri == test_uri

    def test_get_db_name_default(self):
        """Test get_db_name with default value."""
        with patch.dict("os.environ", {}, clear=True):
            name = get_db_name()
            assert name == "uhg_claims"

    def test_get_db_name_from_claims_db_name(self):
        """Test get_db_name from CLAIMS_DB_NAME."""
        with patch.dict("os.environ", {"CLAIMS_DB_NAME": "test_claims"}):
            name = get_db_name()
            assert name == "test_claims"

    def test_get_db_name_from_db_name(self):
        """Test get_db_name from DB_NAME fallback."""
        with patch.dict("os.environ", {"DB_NAME": "test_db"}):
            name = get_db_name()
            assert name == "test_db"


class TestNotificationIntegration:
    """Test cases for notification integration."""

    @pytest.mark.asyncio
    async def test_send_claim_update_notification_success(self):
        """Test successful notification sending."""
        with patch("claims.app.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200

            mock_response.json = lambda: {"notificationId": "test_id"}

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_claim_update_notification(
                "M123", "claim_123", "paid", "Payment processed"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_send_claim_update_notification_failure(self):
        """Test notification sending failure."""
        with patch("claims.app.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_claim_update_notification("M123", "claim_123", "paid")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_claim_update_notification_exception(self):
        """Test notification sending with exception."""
        with patch("claims.app.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Connection error"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_claim_update_notification("M123", "claim_123", "paid")

            assert result is False

    def test_notification_message_customization(self):
        """Test notification message customization by status."""
        status_messages = {
            "adjudicated": "Your claim has been reviewed and adjudicated.",
            "paid": "Great news! Your claim has been approved and payment processed.",
            "denied": "Your claim has been reviewed. Please contact us for details.",
            "pending": "Your claim is currently under review.",
            "submitted": "Your claim has been received and is being processed.",
        }

        for status, expected_message in status_messages.items():
            assert expected_message in status_messages[status]
