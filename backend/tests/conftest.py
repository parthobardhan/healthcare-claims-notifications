import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import date




@pytest.fixture
def mock_db():
    """Mock MongoDB database for testing."""
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    
    db.claims = AsyncMock()
    db.users = AsyncMock()
    db.notifications = AsyncMock()
    db.deliveries = AsyncMock()
    
    db.claims.find_one.return_value = None
    db.users.find_one.return_value = None
    db.notifications.find_one.return_value = None
    db.deliveries.find_one.return_value = None
    
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
        "notes": "Test claim"
    }


@pytest.fixture
def sample_claim_with_id(sample_claim_data):
    """Sample claim data with MongoDB ObjectId."""
    claim_id = ObjectId()
    return {
        "_id": claim_id,
        "id": str(claim_id),
        **sample_claim_data
    }


@pytest.fixture
def sample_notification_data():
    """Sample notification data for testing."""
    return {
        "title": "Test Notification",
        "body": "This is a test notification",
        "icon": "/favicon.ico",
        "url": "http://localhost:4201/",
        "member_id": "M123"
    }


@pytest.fixture
def sample_subscription_data():
    """Sample push subscription data for testing."""
    return {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint",
        "keys": {
            "p256dh": "BNbzJT8ulBGZWHuIXJU_kYXe-4r2-4NzGHe7wjCkQhXoHo6RrqkZNRs",
            "auth": "tBHItJI5svbpez7KI4CCXg"
        }
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "_id": ObjectId(),
        "email": "test@example.com",
        "member_id": "M123",
        "subscriptions": []
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for testing HTTP calls."""
    client = AsyncMock()
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = {"notificationId": "test-notification-id"}
    response.text = "Success"
    client.post.return_value = response
    return client


@pytest.fixture
def mock_webpush():
    """Mock pywebpush.webpush function for testing."""
    return MagicMock()
