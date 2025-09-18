import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from bson import ObjectId
import json

from notify.app import app
from notify.db import get_db
from notify.models import PushSubscription, NotificationCreate
from notify.notify import get_vapid, send_web_push


class TestNotifyApp:
    """Test cases for the notify service."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self, mock_db):
        """Setup test database override."""
        app.dependency_overrides[get_db] = lambda: mock_db
        yield
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health endpoint returns ok status."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_vapid_public_key_endpoint(self):
        """Test VAPID public key endpoint."""
        with patch("notify.app.get_vapid") as mock_get_vapid:
            mock_get_vapid.return_value = {"publicKey": "test_public_key"}

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.get("/vapid-public-key")
                assert response.status_code == 200
                assert response.json() == {"publicKey": "test_public_key"}

    @pytest.mark.asyncio
    async def test_subscribe_new_user_with_email(
        self, mock_db, sample_push_subscription
    ):
        """Test subscribing a new user with email."""
        mock_db.users.find_one = AsyncMock(return_value=None)
        mock_result = AsyncMock()
        mock_result.inserted_id = ObjectId()
        mock_db.users.insert_one = AsyncMock(return_value=mock_result)

        subscription = PushSubscription(**sample_push_subscription)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/subscribe",
                json=subscription.model_dump(),
                params={"email": "test@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "userId" in data

            mock_db.users.find_one.assert_called_once()
            mock_db.users.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_new_user_with_member_id(
        self, mock_db, sample_push_subscription
    ):
        """Test subscribing a new user with member_id."""
        mock_db.users.find_one = AsyncMock(return_value=None)
        mock_result = AsyncMock()
        mock_result.inserted_id = ObjectId()
        mock_db.users.insert_one = AsyncMock(return_value=mock_result)

        subscription = PushSubscription(**sample_push_subscription)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/subscribe",
                json=subscription.model_dump(),
                params={"member_id": "M123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "userId" in data

    @pytest.mark.asyncio
    async def test_subscribe_existing_user_new_subscription(
        self, mock_db, sample_push_subscription, sample_user_with_id
    ):
        """Test adding new subscription to existing user."""
        existing_user = sample_user_with_id.copy()
        existing_user["subscriptions"] = []
        mock_db.users.find_one = AsyncMock(return_value=existing_user)
        mock_db.users.update_one = AsyncMock(return_value=AsyncMock())

        subscription = PushSubscription(**sample_push_subscription)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/subscribe",
                json=subscription.model_dump(),
                params={"email": "test@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["userId"] == str(existing_user["_id"])

            mock_db.users.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_existing_user_existing_subscription(
        self, mock_db, sample_push_subscription, sample_user_with_id
    ):
        """Test subscribing with existing subscription (no-op)."""
        existing_user = sample_user_with_id.copy()
        existing_user["subscriptions"] = [sample_push_subscription]
        mock_db.users.find_one = AsyncMock(return_value=existing_user)
        mock_db.users.update_one = AsyncMock(return_value=AsyncMock())

        subscription = PushSubscription(**sample_push_subscription)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/subscribe",
                json=subscription.model_dump(),
                params={"email": "test@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["userId"] == str(existing_user["_id"])

            mock_db.users.update_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_to_specific_member(
        self, mock_db, sample_notification_data, sample_user_with_id
    ):
        """Test sending notification to specific member."""
        notification = NotificationCreate(**sample_notification_data)

        mock_result = AsyncMock()
        mock_result.inserted_id = ObjectId()
        mock_db.notifications.insert_one = AsyncMock(return_value=mock_result)

        class MockCursor:
            def __init__(self, data):
                self.data = data

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.data:
                    return self.data.pop(0)
                raise StopAsyncIteration

        mock_db.users.find = lambda *args, **kwargs: MockCursor([sample_user_with_id])
        mock_db.deliveries.insert_one = AsyncMock(return_value=AsyncMock())

        with patch("notify.app.send_web_push"):
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/notify",
                    json=notification.model_dump(),
                    params={"member_id": "M123"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert data["successful"] == 1
                assert data["failed"] == 0
                assert "notificationId" in data

                mock_db.notifications.insert_one.assert_called_once()
                mock_db.deliveries.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_to_all_users(
        self, mock_db, sample_notification_data, sample_user_with_id
    ):
        """Test sending notification to all users."""
        notification = NotificationCreate(**sample_notification_data)
        notification.member_id = None

        mock_result = AsyncMock()
        mock_result.inserted_id = ObjectId()
        mock_db.notifications.insert_one = AsyncMock(return_value=mock_result)

        class MockCursor:
            def __init__(self, data):
                self.data = data

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.data:
                    return self.data.pop(0)
                raise StopAsyncIteration

        mock_db.users.find = lambda *args, **kwargs: MockCursor([sample_user_with_id])
        mock_db.deliveries.insert_one = AsyncMock(return_value=AsyncMock())

        with patch("notify.app.send_web_push"):
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/notify", json=notification.model_dump(exclude_none=True)
                )

                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert data["successful"] == 1
                assert data["failed"] == 0

    @pytest.mark.asyncio
    async def test_notify_web_push_failure(
        self, mock_db, sample_notification_data, sample_user_with_id
    ):
        """Test handling web push failure."""
        notification = NotificationCreate(**sample_notification_data)

        mock_result = AsyncMock()
        mock_result.inserted_id = ObjectId()
        mock_db.notifications.insert_one = AsyncMock(return_value=mock_result)

        class MockCursor:
            def __init__(self, data):
                self.data = data

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.data:
                    return self.data.pop(0)
                raise StopAsyncIteration

        mock_db.users.find = lambda *args, **kwargs: MockCursor([sample_user_with_id])
        mock_db.deliveries.insert_one = AsyncMock(return_value=AsyncMock())

        with patch("notify.app.send_web_push") as mock_send_web_push:
            mock_send_web_push.side_effect = Exception("Web push failed")

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/notify",
                    json=notification.model_dump(),
                    params={"member_id": "M123"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert data["successful"] == 0
                assert data["failed"] == 1

    @pytest.mark.asyncio
    async def test_notify_subscription_removal_on_410_error(
        self, mock_db, sample_notification_data, sample_user_with_id
    ):
        """Test subscription removal on 410 error."""
        notification = NotificationCreate(**sample_notification_data)

        mock_result = AsyncMock()
        mock_result.inserted_id = ObjectId()
        mock_db.notifications.insert_one = AsyncMock(return_value=mock_result)

        class MockCursor:
            def __init__(self, data):
                self.data = data

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.data:
                    return self.data.pop(0)
                raise StopAsyncIteration

        mock_db.users.find = lambda *args, **kwargs: MockCursor([sample_user_with_id])
        mock_db.users.update_one = AsyncMock(return_value=AsyncMock())
        mock_db.deliveries.insert_one = AsyncMock(return_value=AsyncMock())

        with patch("notify.app.send_web_push") as mock_send_web_push:
            error = Exception("Web push failed")
            error.response = MagicMock()
            error.response.status_code = 410
            mock_send_web_push.side_effect = error

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/notify",
                    json=notification.model_dump(),
                    params={"member_id": "M123"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert len(data["removed"]) == 1

                mock_db.users.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_invalid_user_id(self, mock_db, sample_notification_data):
        """Test notification with invalid user_id."""
        notification = NotificationCreate(**sample_notification_data)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/notify",
                json=notification.model_dump(),
                params={"user_id": "invalid_id"},
            )

            assert response.status_code == 400
            assert "Invalid user_id" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_users(self, mock_db, sample_user_with_id):
        """Test listing users endpoint."""

        class MockCursor:
            def __init__(self, data):
                self.data = data

            def limit(self, count):
                return self

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.data:
                    return self.data.pop(0)
                raise StopAsyncIteration

        mock_db.users.find = lambda *args, **kwargs: MockCursor([sample_user_with_id])

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/users")

            assert response.status_code == 200
            users = response.json()
            assert len(users) == 1
            assert users[0]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_list_notifications(self, mock_db):
        """Test listing notifications endpoint."""
        notification_doc = {
            "_id": ObjectId(),
            "title": "Test Notification",
            "body": "Test body",
            "audience": "all",
        }

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
                    return self.data.pop(0)
                raise StopAsyncIteration

        mock_db.notifications.find = lambda *args, **kwargs: MockCursor(
            [notification_doc]
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/notifications")

            assert response.status_code == 200
            notifications = response.json()
            assert len(notifications) == 1
            assert notifications[0]["title"] == "Test Notification"

    @pytest.mark.asyncio
    async def test_list_deliveries(self, mock_db):
        """Test listing deliveries endpoint."""
        delivery_doc = {
            "_id": ObjectId(),
            "notification_id": str(ObjectId()),
            "user_id": str(ObjectId()),
            "endpoint": "https://test.com",
            "status": "sent",
        }

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
                    return self.data.pop(0)
                raise StopAsyncIteration

        mock_db.deliveries.find = lambda *args, **kwargs: MockCursor([delivery_doc])

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/deliveries")

            assert response.status_code == 200
            deliveries = response.json()
            assert len(deliveries) == 1
            assert deliveries[0]["status"] == "sent"


class TestNotifyUtils:
    """Test cases for notify utility functions."""

    def test_get_vapid_with_env_vars(self):
        """Test get_vapid with environment variables."""
        with patch.dict(
            "os.environ",
            {
                "VAPID_PUBLIC_KEY": "test_public",
                "VAPID_PRIVATE_KEY": "test_private",
                "VAPID_SUBJECT": "test@example.com",
            },
        ):
            vapid = get_vapid()
            assert vapid["publicKey"] == "test_public"
            assert vapid["privateKey"] == "test_private"
            assert vapid["subject"] == "mailto:test@example.com"

    def test_get_vapid_with_defaults(self):
        """Test get_vapid with default values."""
        with patch.dict("os.environ", {}, clear=True):
            vapid = get_vapid()
            assert "publicKey" in vapid
            assert "privateKey" in vapid
            assert vapid["subject"].startswith("mailto:")

    def test_get_vapid_subject_formatting(self):
        """Test VAPID subject formatting."""
        with patch.dict("os.environ", {"VAPID_SUBJECT": "admin@test.com"}):
            vapid = get_vapid()
            assert vapid["subject"] == "mailto:admin@test.com"

    def test_send_web_push_success(self, sample_push_subscription):
        """Test successful web push sending."""
        with patch("pywebpush.webpush") as mock_webpush:
            payload = {"title": "Test", "body": "Test message"}
            send_web_push(sample_push_subscription, payload)

            mock_webpush.assert_called_once()
            args, kwargs = mock_webpush.call_args
            assert kwargs["subscription_info"] == sample_push_subscription
            assert json.loads(kwargs["data"]) == payload

    def test_send_web_push_exception(self, sample_push_subscription):
        """Test web push exception handling."""
        from pywebpush import WebPushException

        with patch("pywebpush.webpush") as mock_webpush:
            mock_webpush.side_effect = WebPushException("Test error")

            payload = {"title": "Test", "body": "Test message"}

            with pytest.raises(WebPushException):
                send_web_push(sample_push_subscription, payload)
