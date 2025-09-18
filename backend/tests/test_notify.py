import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId
from datetime import datetime

from notify.app import app
from notify.db import get_db
from notify.models import NotificationCreate, PushSubscription, User
from notify.notify import get_vapid, send_web_push


@pytest.fixture
def mock_notify_db():
    """Mock database for notify service tests."""
    db = AsyncMock()
    
    class AsyncIteratorMock:
        def __init__(self, items=None):
            self.items = items or []
            self.index = 0
            
        def __aiter__(self):
            return self
            
        async def __anext__(self):
            if self.index >= len(self.items):
                raise StopAsyncIteration
            item = self.items[self.index]
            self.index += 1
            return item
            
        def limit(self, count):
            return self
            
        def sort(self, field, direction=1):
            return self
    
    db.users = AsyncMock()
    db.users.find_one = AsyncMock()
    db.users.insert_one = AsyncMock()
    db.users.update_one = AsyncMock()
    db.users.find = MagicMock(return_value=AsyncIteratorMock())
    
    db.notifications = AsyncMock()
    db.notifications.insert_one = AsyncMock()
    db.notifications.find = MagicMock(return_value=AsyncIteratorMock())
    
    db.deliveries = AsyncMock()
    db.deliveries.insert_one = AsyncMock()
    db.deliveries.find = MagicMock(return_value=AsyncIteratorMock())
    
    return db


@pytest.fixture(autouse=True)
def setup_notify_test_db(mock_notify_db):
    """Setup mock database for notify service."""
    def _override_db():
        return mock_notify_db

    app.dependency_overrides[get_db] = _override_db
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test notify service health endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
@patch("notify.notify.get_vapid")
async def test_vapid_public_key_endpoint(mock_get_vapid):
    """Test VAPID public key endpoint."""
    mock_get_vapid.return_value = {"publicKey": "test-public-key"}
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/vapid-public-key")
        assert r.status_code == 200
        assert r.json() == {"publicKey": "test-public-key"}


@pytest.mark.asyncio
async def test_subscribe_new_user_with_email(mock_notify_db):
    """Test subscribing a new user with email."""
    mock_notify_db.users.find_one.return_value = None  # User doesn't exist
    mock_insert_result = AsyncMock()
    mock_insert_result.inserted_id = ObjectId()
    mock_notify_db.users.insert_one.return_value = mock_insert_result

    subscription_data = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {
            "p256dh": "test-p256dh",
            "auth": "test-auth"
        }
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/subscribe",
            json=subscription_data,
            params={"email": "test@example.com"}
        )
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["ok"] is True
        assert "userId" in response_data

    mock_notify_db.users.find_one.assert_called_once_with({"email": "test@example.com"})
    mock_notify_db.users.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_subscribe_new_user_with_member_id(mock_notify_db):
    """Test subscribing a new user with member_id."""
    mock_notify_db.users.find_one.return_value = None
    mock_insert_result = AsyncMock()
    mock_insert_result.inserted_id = ObjectId()
    mock_notify_db.users.insert_one.return_value = mock_insert_result

    subscription_data = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {
            "p256dh": "test-p256dh",
            "auth": "test-auth"
        }
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/subscribe",
            json=subscription_data,
            params={"member_id": "M123"}
        )
        assert r.status_code == 200

    mock_notify_db.users.find_one.assert_called_once_with({"member_id": "M123"})


@pytest.mark.asyncio
async def test_subscribe_existing_user_new_subscription(mock_notify_db):
    """Test adding subscription to existing user."""
    user_id = ObjectId()
    existing_user = {
        "_id": user_id,
        "email": "test@example.com",
        "subscriptions": []
    }
    mock_notify_db.users.find_one.return_value = existing_user

    subscription_data = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {
            "p256dh": "test-p256dh",
            "auth": "test-auth"
        }
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/subscribe",
            json=subscription_data,
            params={"email": "test@example.com"}
        )
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["userId"] == str(user_id)

    mock_notify_db.users.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_subscribe_existing_user_existing_subscription(mock_notify_db):
    """Test subscribing with existing endpoint."""
    user_id = ObjectId()
    existing_user = {
        "_id": user_id,
        "email": "test@example.com",
        "subscriptions": [{
            "endpoint": "https://fcm.googleapis.com/fcm/send/test",
            "keys": {"p256dh": "test-p256dh", "auth": "test-auth"}
        }]
    }
    mock_notify_db.users.find_one.return_value = existing_user

    subscription_data = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {
            "p256dh": "test-p256dh",
            "auth": "test-auth"
        }
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/subscribe",
            json=subscription_data,
            params={"email": "test@example.com"}
        )
        assert r.status_code == 200

    mock_notify_db.users.update_one.assert_not_called()


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_broadcast_success(mock_send_web_push, mock_db):
    """Test broadcasting notification to all users."""
    notification_id = ObjectId()
    mock_insert_result = AsyncMock()
    mock_insert_result.inserted_id = notification_id
    mock_notify_db.notifications.insert_one.return_value = mock_insert_result

    users = [
        {
            "_id": ObjectId(),
            "email": "user1@example.com",
            "subscriptions": [{
                "endpoint": "https://fcm.googleapis.com/fcm/send/user1",
                "keys": {"p256dh": "key1", "auth": "auth1"}
            }]
        },
        {
            "_id": ObjectId(),
            "email": "user2@example.com",
            "subscriptions": [{
                "endpoint": "https://fcm.googleapis.com/fcm/send/user2",
                "keys": {"p256dh": "key2", "auth": "auth2"}
            }]
        }
    ]
    
    async def mock_find():
        for user in users:
            yield user
    
    mock_notify_db.users.find.return_value = mock_find()

    notification_data = {
        "title": "Test Notification",
        "body": "Test message",
        "icon": "/favicon.ico",
        "url": "http://localhost:4201/"
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/notify", json=notification_data)
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["ok"] is True
        assert response_data["successful"] == 2
        assert response_data["failed"] == 0
        assert response_data["notificationId"] == str(notification_id)

    assert mock_send_web_push.call_count == 2


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_member_specific(mock_send_web_push, mock_db):
    """Test sending notification to specific member."""
    notification_id = ObjectId()
    mock_insert_result = AsyncMock()
    mock_insert_result.inserted_id = notification_id
    mock_notify_db.notifications.insert_one.return_value = mock_insert_result

    target_user = {
        "_id": ObjectId(),
        "member_id": "M123",
        "subscriptions": [{
            "endpoint": "https://fcm.googleapis.com/fcm/send/member123",
            "keys": {"p256dh": "key1", "auth": "auth1"}
        }]
    }
    
    async def mock_find():
        yield target_user
    
    mock_notify_db.users.find.return_value = mock_find()

    notification_data = {
        "title": "Member Notification",
        "body": "Your claim has been updated",
        "member_id": "M123"
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/notify", json=notification_data)
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["successful"] == 1

    mock_notify_db.users.find.assert_called_once_with({"member_id": "M123"})


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_user_specific(mock_send_web_push, mock_db):
    """Test sending notification to specific user by user_id."""
    notification_id = ObjectId()
    user_id = ObjectId()
    mock_insert_result = AsyncMock()
    mock_insert_result.inserted_id = notification_id
    mock_notify_db.notifications.insert_one.return_value = mock_insert_result

    target_user = {
        "_id": user_id,
        "email": "user@example.com",
        "subscriptions": [{
            "endpoint": "https://fcm.googleapis.com/fcm/send/user",
            "keys": {"p256dh": "key1", "auth": "auth1"}
        }]
    }
    
    async def mock_find():
        yield target_user
    
    mock_notify_db.users.find.return_value = mock_find()

    notification_data = {
        "title": "User Notification",
        "body": "Personal message"
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/notify",
            json=notification_data,
            params={"user_id": str(user_id)}
        )
        assert r.status_code == 200

    mock_notify_db.users.find.assert_called_once_with({"_id": user_id})


@pytest.mark.asyncio
async def test_notify_invalid_user_id(mock_notify_db):
    """Test notification with invalid user_id."""
    notification_data = {
        "title": "Test",
        "body": "Test message"
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/notify",
            json=notification_data,
            params={"user_id": "invalid-id"}
        )
        assert r.status_code == 400
        assert "Invalid user_id" in r.json()["detail"]


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_web_push_failure_410(mock_send_web_push, mock_notify_db):
    """Test handling web push failure with 410 status (subscription expired)."""
    from pywebpush import WebPushException
    
    notification_id = ObjectId()
    mock_insert_result = AsyncMock()
    mock_insert_result.inserted_id = notification_id
    mock_notify_db.notifications.insert_one.return_value = mock_insert_result

    mock_response = MagicMock()
    mock_response.status_code = 410
    exception = WebPushException("Subscription expired")
    exception.response = mock_response
    mock_send_web_push.side_effect = exception

    user = {
        "_id": ObjectId(),
        "subscriptions": [{
            "endpoint": "https://fcm.googleapis.com/fcm/send/expired",
            "keys": {"p256dh": "key1", "auth": "auth1"}
        }]
    }
    
    async def mock_find():
        yield user
    
    mock_notify_db.users.find.return_value = mock_find()

    notification_data = {
        "title": "Test",
        "body": "Test message"
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/notify", json=notification_data)
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["failed"] == 1
        assert len(response_data["removed"]) == 1

    mock_notify_db.users.update_one.assert_called_once()


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_web_push_failure_other(mock_send_web_push, mock_notify_db):
    """Test handling web push failure with other status codes."""
    from pywebpush import WebPushException
    
    notification_id = ObjectId()
    mock_insert_result = AsyncMock()
    mock_insert_result.inserted_id = notification_id
    mock_notify_db.notifications.insert_one.return_value = mock_insert_result

    mock_response = MagicMock()
    mock_response.status_code = 500
    exception = WebPushException("Server error")
    exception.response = mock_response
    mock_send_web_push.side_effect = exception

    user = {
        "_id": ObjectId(),
        "subscriptions": [{
            "endpoint": "https://fcm.googleapis.com/fcm/send/error",
            "keys": {"p256dh": "key1", "auth": "auth1"}
        }]
    }
    
    async def mock_find():
        yield user
    
    mock_notify_db.users.find.return_value = mock_find()

    notification_data = {
        "title": "Test",
        "body": "Test message"
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/notify", json=notification_data)
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["failed"] == 1
        assert len(response_data["removed"]) == 0  # Should not remove on 500 error


@pytest.mark.asyncio
async def test_list_users(mock_notify_db):
    """Test listing users endpoint."""
    users = [
        {"_id": ObjectId(), "email": "user1@example.com", "subscriptions": []},
        {"_id": ObjectId(), "email": "user2@example.com", "subscriptions": []}
    ]
    
    mock_notify_db.users.find.return_value.items = users

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/users")
        assert r.status_code == 200
        response_data = r.json()
        assert len(response_data) == 2


@pytest.mark.asyncio
async def test_list_notifications(mock_notify_db):
    """Test listing notifications endpoint."""
    notifications = [
        {"_id": ObjectId(), "title": "Test 1", "body": "Message 1"},
        {"_id": ObjectId(), "title": "Test 2", "body": "Message 2"}
    ]
    
    mock_notify_db.notifications.find.return_value.items = notifications

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/notifications")
        assert r.status_code == 200
        response_data = r.json()
        assert len(response_data) == 2


@pytest.mark.asyncio
async def test_list_deliveries(mock_notify_db):
    """Test listing deliveries endpoint."""
    deliveries = [
        {"_id": ObjectId(), "notification_id": "123", "status": "sent"},
        {"_id": ObjectId(), "notification_id": "456", "status": "failed"}
    ]
    
    mock_notify_db.deliveries.find.return_value.items = deliveries

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/deliveries")
        assert r.status_code == 200
        response_data = r.json()
        assert len(response_data) == 2


@patch.dict("os.environ", {
    "VAPID_PUBLIC_KEY": "test-public",
    "VAPID_PRIVATE_KEY": "test-private",
    "VAPID_SUBJECT": "test@example.com"
})
def test_get_vapid_from_env():
    """Test VAPID key retrieval from environment variables."""
    vapid = get_vapid()
    assert vapid["publicKey"] == "test-public"
    assert vapid["privateKey"] == "test-private"
    assert vapid["subject"] == "mailto:test@example.com"


@patch.dict("os.environ", {}, clear=True)
def test_get_vapid_defaults():
    """Test VAPID key retrieval with default values."""
    vapid = get_vapid()
    assert "BDMDBW7Xk4LErBOYtpIxdROk7gtr40VIY6r_aWYbjwP3l4Nu04yaBfcABCwYS87PO69sXyLJ1l9oHo6RrqkZNRs" in vapid["publicKey"]
    assert vapid["subject"].startswith("mailto:")


@patch("pywebpush.webpush")
def test_send_web_push_success(mock_webpush):
    """Test successful web push sending."""
    subscription = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {"p256dh": "key", "auth": "auth"}
    }
    payload = {"title": "Test", "body": "Message"}
    
    send_web_push(subscription, payload)
    
    mock_webpush.assert_called_once()
    call_args = mock_webpush.call_args
    assert call_args[1]["subscription_info"] == subscription


@patch("pywebpush.webpush")
def test_send_web_push_exception(mock_webpush):
    """Test web push sending with exception."""
    from pywebpush import WebPushException
    
    mock_webpush.side_effect = WebPushException("Test error")
    
    subscription = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {"p256dh": "key", "auth": "auth"}
    }
    payload = {"title": "Test", "body": "Message"}
    
    with pytest.raises(WebPushException):
        send_web_push(subscription, payload)


def test_notification_models():
    """Test Pydantic models for notifications."""
    notification_data = {
        "title": "Test Title",
        "body": "Test Body",
        "icon": "/icon.png",
        "url": "http://example.com",
        "member_id": "M123"
    }
    
    notification = NotificationCreate(**notification_data)
    assert notification.title == "Test Title"
    assert notification.member_id == "M123"
    
    subscription_data = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {
            "p256dh": "test-key",
            "auth": "test-auth"
        }
    }
    
    subscription = PushSubscription(**subscription_data)
    assert subscription.endpoint == "https://fcm.googleapis.com/fcm/send/test"
    assert subscription.keys.p256dh == "test-key"
    
    user_data = {
        "email": "test@example.com",
        "member_id": "M123",
        "subscriptions": [subscription_data]
    }
    
    user = User(**user_data)
    assert user.email == "test@example.com"
    assert len(user.subscriptions) == 1


def test_notification_create_minimal():
    """Test NotificationCreate with minimal required fields."""
    notification = NotificationCreate(title="Test", body="Message")
    assert notification.title == "Test"
    assert notification.body == "Message"
    assert notification.icon is None
    assert notification.url is None
    assert notification.member_id is None


def test_push_subscription_validation():
    """Test PushSubscription validation."""
    valid_data = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {
            "p256dh": "test-key",
            "auth": "test-auth"
        }
    }
    subscription = PushSubscription(**valid_data)
    assert subscription.endpoint == "https://fcm.googleapis.com/fcm/send/test"
    
    with pytest.raises(Exception):  # Pydantic validation error
        PushSubscription(endpoint="https://test.com")
