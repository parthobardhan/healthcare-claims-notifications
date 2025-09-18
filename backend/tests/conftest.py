import pytest
from unittest.mock import AsyncMock, MagicMock
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId


@pytest.fixture
def mock_db():
    """Mock database fixture for testing."""
    db = AsyncMock(spec=AsyncIOMotorDatabase)

    db.claims = AsyncMock()
    db.users = AsyncMock()
    db.notifications = AsyncMock()
    db.deliveries = AsyncMock()

    return db


@pytest.fixture
def sample_claim_data():
    """Sample claim data for testing."""
    return {
        "member_id": "M123",
        "provider_id": "P456",
        "service_date": "2025-09-01",
        "received_date": "2025-09-02",
        "diagnosis_codes": ["E11.9"],
        "procedure_codes": ["99213"],
        "amount_billed": 120.0,
        "amount_allowed": 100.0,
        "amount_paid": 80.0,
        "status": "submitted",
        "notes": "Test claim",
    }


@pytest.fixture
def sample_claim_with_id(sample_claim_data):
    """Sample claim data with ObjectId."""
    claim_id = ObjectId()
    return {"_id": claim_id, "id": str(claim_id), **sample_claim_data}


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "member_id": "M123",
        "subscriptions": [
            {
                "endpoint": "https://fcm.googleapis.com/fcm/send/test",
                "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
            }
        ],
    }


@pytest.fixture
def sample_user_with_id(sample_user_data):
    """Sample user data with ObjectId."""
    user_id = ObjectId()
    return {"_id": user_id, "id": str(user_id), **sample_user_data}


@pytest.fixture
def sample_notification_data():
    """Sample notification data for testing."""
    return {
        "title": "Test Notification",
        "body": "This is a test notification",
        "icon": "/favicon.ico",
        "url": "http://localhost:4201/",
        "member_id": "M123",
    }


@pytest.fixture
def sample_push_subscription():
    """Sample push subscription data for testing."""
    return {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for testing."""
    client = AsyncMock()
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = {"notificationId": "test_notification_id"}
    response.text = "Success"
    client.post.return_value = response
    return client


@pytest.fixture
def mock_webpush():
    """Mock webpush function for testing."""
    return MagicMock()
