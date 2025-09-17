import os
import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from unittest.mock import patch, MagicMock

from notify.app import app
from notify.db import get_db

TEST_DB_NAME = "web_notifications_test"


@pytest.fixture(autouse=True, scope="function")
async def setup_test_db():
    # Use test DB; assumes MONGODB_URI points to a local or Atlas test cluster
    os.environ["NOTIFICATIONS_DB_NAME"] = TEST_DB_NAME

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
        await db.drop_collection("users")
        await db.drop_collection("notifications")
        await db.drop_collection("deliveries")
    except Exception:
        pass

    try:
        client.close()
    except Exception:
        pass

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_vapid_public_key():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/vapid-public-key")
        assert r.status_code == 200
        data = r.json()
        assert "publicKey" in data
        assert len(data["publicKey"]) > 0


@pytest.mark.asyncio
async def test_subscribe_new_user_with_email():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }

        r = await ac.post(
            "/subscribe", json=subscription_data, params={"email": "test@example.com"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "userId" in data


@pytest.mark.asyncio
async def test_subscribe_new_user_with_member_id():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test456",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }

        r = await ac.post(
            "/subscribe", json=subscription_data, params={"member_id": "M123"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True


@pytest.mark.asyncio
async def test_subscribe_new_user_no_params():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test789",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }

        r = await ac.post("/subscribe", json=subscription_data)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True


@pytest.mark.asyncio
async def test_subscribe_existing_user_same_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }

        r1 = await ac.post(
            "/subscribe", json=subscription_data, params={"email": "test@example.com"}
        )
        assert r1.status_code == 200

        r2 = await ac.post(
            "/subscribe", json=subscription_data, params={"email": "test@example.com"}
        )
        assert r2.status_code == 200
        assert r1.json()["userId"] == r2.json()["userId"]


@pytest.mark.asyncio
async def test_subscribe_existing_user_new_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data1 = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }

        subscription_data2 = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test456",
            "keys": {"p256dh": "test_p256dh_key2", "auth": "test_auth_key2"},
        }

        r1 = await ac.post(
            "/subscribe", json=subscription_data1, params={"email": "test@example.com"}
        )
        assert r1.status_code == 200

        r2 = await ac.post(
            "/subscribe", json=subscription_data2, params={"email": "test@example.com"}
        )
        assert r2.status_code == 200
        assert r1.json()["userId"] == r2.json()["userId"]


@pytest.mark.asyncio
async def test_subscribe_update_member_id():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }

        r1 = await ac.post(
            "/subscribe", json=subscription_data, params={"email": "test@example.com"}
        )
        assert r1.status_code == 200

        r2 = await ac.post(
            "/subscribe",
            json=subscription_data,
            params={"email": "test@example.com", "member_id": "M123"},
        )
        assert r2.status_code == 200
        assert r1.json()["userId"] == r2.json()["userId"]


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_all_users(mock_send_web_push):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }
        await ac.post(
            "/subscribe", json=subscription_data, params={"email": "test@example.com"}
        )

        notification_data = {
            "title": "Test Notification",
            "body": "This is a test notification",
            "icon": "/favicon.ico",
            "url": "http://localhost:4201/",
        }

        r = await ac.post("/notify", json=notification_data)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "notificationId" in data
        assert data["successful"] == 1
        assert data["failed"] == 0

        mock_send_web_push.assert_called_once()


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_specific_member(mock_send_web_push):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }
        await ac.post(
            "/subscribe", json=subscription_data, params={"member_id": "M123"}
        )

        notification_data = {
            "title": "Member Notification",
            "body": "This is for member M123",
            "member_id": "M123",
        }

        r = await ac.post("/notify", json=notification_data)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["successful"] == 1

        mock_send_web_push.assert_called_once()


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_specific_user_id(mock_send_web_push):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }
        r = await ac.post(
            "/subscribe", json=subscription_data, params={"email": "test@example.com"}
        )
        user_id = r.json()["userId"]

        notification_data = {
            "title": "User Notification",
            "body": "This is for specific user",
        }

        r = await ac.post(
            "/notify", json=notification_data, params={"user_id": user_id}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["successful"] == 1


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_invalid_user_id(mock_send_web_push):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        notification_data = {
            "title": "User Notification",
            "body": "This is for invalid user",
        }

        r = await ac.post(
            "/notify", json=notification_data, params={"user_id": "invalid_id"}
        )
        assert r.status_code == 400
        assert "Invalid user_id" in r.json()["detail"]


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_no_matching_users(mock_send_web_push):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        notification_data = {
            "title": "Member Notification",
            "body": "This is for non-existent member",
            "member_id": "M999",
        }

        r = await ac.post("/notify", json=notification_data)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["successful"] == 0
        assert data["failed"] == 0

        mock_send_web_push.assert_not_called()


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_web_push_failure(mock_send_web_push):
    from pywebpush import WebPushException

    mock_send_web_push.side_effect = WebPushException("Push failed")

    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }
        await ac.post(
            "/subscribe", json=subscription_data, params={"email": "test@example.com"}
        )

        notification_data = {"title": "Test Notification", "body": "This should fail"}

        r = await ac.post("/notify", json=notification_data)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["failed"] == 1
        assert data["successful"] == 0


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_notify_web_push_subscription_removal(mock_send_web_push):
    from pywebpush import WebPushException

    mock_response = MagicMock()
    mock_response.status_code = 410
    mock_response.text = "Gone"

    exception = WebPushException("Subscription expired")
    exception.response = mock_response
    mock_send_web_push.side_effect = exception

    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }
        await ac.post(
            "/subscribe", json=subscription_data, params={"email": "test@example.com"}
        )

        notification_data = {
            "title": "Test Notification",
            "body": "This should remove subscription",
        }

        r = await ac.post("/notify", json=notification_data)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert len(data["removed"]) == 1
        assert data["removed"][0] == "https://fcm.googleapis.com/fcm/send/test123"


@pytest.mark.asyncio
async def test_list_users_empty():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/users")
        assert r.status_code == 200
        users = r.json()
        assert users == []


@pytest.mark.asyncio
async def test_list_users_with_data():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }
        await ac.post(
            "/subscribe",
            json=subscription_data,
            params={"email": "test@example.com", "member_id": "M123"},
        )

        r = await ac.get("/users")
        assert r.status_code == 200
        users = r.json()
        assert len(users) == 1
        assert users[0]["email"] == "test@example.com"
        assert users[0]["member_id"] == "M123"
        assert len(users[0]["subscriptions"]) == 1


@pytest.mark.asyncio
async def test_list_notifications_empty():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/notifications")
        assert r.status_code == 200
        notifications = r.json()
        assert notifications == []


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_list_notifications_with_data(mock_send_web_push):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }
        await ac.post(
            "/subscribe", json=subscription_data, params={"email": "test@example.com"}
        )

        notification_data = {
            "title": "Test Notification",
            "body": "This is a test notification",
        }
        await ac.post("/notify", json=notification_data)

        r = await ac.get("/notifications")
        assert r.status_code == 200
        notifications = r.json()
        assert len(notifications) == 1
        assert notifications[0]["title"] == "Test Notification"
        assert notifications[0]["body"] == "This is a test notification"
        assert notifications[0]["audience"] == "all"


@pytest.mark.asyncio
async def test_list_deliveries_empty():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/deliveries")
        assert r.status_code == 200
        deliveries = r.json()
        assert deliveries == []


@pytest.mark.asyncio
@patch("notify.notify.send_web_push")
async def test_list_deliveries_with_data(mock_send_web_push):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }
        await ac.post(
            "/subscribe", json=subscription_data, params={"email": "test@example.com"}
        )

        notification_data = {
            "title": "Test Notification",
            "body": "This is a test notification",
        }
        await ac.post("/notify", json=notification_data)

        r = await ac.get("/deliveries")
        assert r.status_code == 200
        deliveries = r.json()
        assert len(deliveries) == 1
        assert deliveries[0]["status"] == "sent"
        assert (
            deliveries[0]["endpoint"] == "https://fcm.googleapis.com/fcm/send/test123"
        )


@pytest.mark.asyncio
async def test_notify_payload_member_id_priority():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }
        await ac.post(
            "/subscribe", json=subscription_data, params={"member_id": "M123"}
        )

        notification_data = {
            "title": "Member Notification",
            "body": "This is for member M456",
            "member_id": "M456",
        }

        with patch("notify.notify.send_web_push") as mock_send_web_push:
            r = await ac.post(
                "/notify", json=notification_data, params={"member_id": "M123"}
            )
            assert r.status_code == 200
            data = r.json()
            assert data["ok"] is True
            assert data["successful"] == 0
            mock_send_web_push.assert_not_called()
