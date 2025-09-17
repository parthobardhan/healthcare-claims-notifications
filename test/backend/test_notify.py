import os
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from httpx import AsyncClient
from bson import ObjectId
import json
from datetime import datetime

from notify.app import app
from notify.db import get_db
from notify.models import NotificationCreate, PushSubscription, SubscriptionKeys


class MockAsyncCollection:
    """Mock async MongoDB collection"""

    def __init__(self):
        self.data = []
        self.inserted_ids = []

    async def find_one(self, query):
        for item in self.data:
            if self._matches_query(item, query):
                return item
        return None

    def find(self, query=None, limit=None):
        results = []
        for item in self.data:
            if query is None or self._matches_query(item, query):
                results.append(item)
        if limit:
            results = results[:limit]
        return MockAsyncCursor(results)

    async def insert_one(self, document):
        doc_id = ObjectId()
        doc_copy = document.copy()
        doc_copy["_id"] = doc_id
        self.data.append(doc_copy)
        result = Mock()
        result.inserted_id = doc_id
        return result

    async def insert_many(self, documents):
        inserted_ids = []
        for doc in documents:
            result = await self.insert_one(doc)
            inserted_ids.append(result.inserted_id)
        result = Mock()
        result.inserted_ids = inserted_ids
        return result

    async def update_one(self, query, update):
        for item in self.data:
            if self._matches_query(item, query):
                if "$push" in update:
                    for field, value in update["$push"].items():
                        if field not in item:
                            item[field] = []
                        item[field].append(value)
                if "$set" in update:
                    for field, value in update["$set"].items():
                        item[field] = value
                if "$pull" in update:
                    for field, pull_query in update["$pull"].items():
                        if field in item and isinstance(item[field], list):
                            item[field] = [x for x in item[field] if not self._matches_query(x, pull_query)]
                break

    async def count_documents(self, query):
        count = 0
        for item in self.data:
            if self._matches_query(item, query):
                count += 1
        return count

    async def drop_collection(self):
        self.data.clear()

    def sort(self, field, direction):
        return self

    def limit(self, count):
        return self

    def _matches_query(self, item, query):
        if not query:
            return True
        for key, value in query.items():
            if key == "_id":
                # Handle ObjectId comparison
                item_id = item.get(key)
                if isinstance(item_id, ObjectId):
                    item_id = str(item_id)
                if isinstance(value, ObjectId):
                    value = str(value)
                if str(item_id) != str(value):
                    return False
            elif key == "member_id":
                # Handle member_id filtering specifically
                item_member_id = item.get(key)
                if item_member_id != value:
                    return False
            elif item.get(key) != value:
                return False
        return True


class MockAsyncCursor:
    """Mock async cursor for MongoDB results"""

    def __init__(self, data):
        self.data = data
        self.index = 0
        self._limit = None
        self._sort_field = None
        self._sort_direction = None

    def limit(self, count):
        """Apply limit to results"""
        self._limit = count
        return self

    def sort(self, field, direction=1):
        """Apply sort to results"""
        self._sort_field = field
        self._sort_direction = direction
        return self

    def _apply_modifiers(self):
        """Apply sort and limit modifiers to data"""
        data = self.data[:]

        if self._sort_field:
            # Simple sort implementation
            reverse = self._sort_direction == -1
            data.sort(key=lambda x: str(x.get(self._sort_field, "")), reverse=reverse)

        if self._limit:
            data = data[:self._limit]

        return data

    def __aiter__(self):
        self.index = 0
        self._processed_data = self._apply_modifiers()
        return self

    async def __anext__(self):
        if self.index >= len(self._processed_data):
            raise StopAsyncIteration
        result = self._processed_data[self.index]
        self.index += 1
        return result


class MockDatabase:
    """Mock async MongoDB database"""

    def __init__(self):
        self.users = MockAsyncCollection()
        self.notifications = MockAsyncCollection()
        self.deliveries = MockAsyncCollection()

    async def drop_collection(self, collection_name):
        getattr(self, collection_name).data.clear()


@pytest.fixture(autouse=True)
def setup_mock_db():
    """Setup mock database for each test"""
    mock_db = MockDatabase()

    async def _mock_get_db():
        return mock_db

    # Override the database dependency
    app.dependency_overrides[get_db] = _mock_get_db

    try:
        yield mock_db
    finally:
        # Clean up dependency overrides
            app.dependency_overrides.clear()


@pytest.fixture
def mock_subscription():
    """Create a mock push subscription"""
    return PushSubscription(
        endpoint="https://fcm.googleapis.com/fcm/send/test-endpoint",
        keys=SubscriptionKeys(p256dh="test-p256dh-key", auth="test-auth-key"),
    )


@pytest.fixture
def mock_notification():
    """Create a mock notification payload"""
    return NotificationCreate(
        title="Test Notification",
        body="This is a test notification",
        icon="/test-icon.png",
        url="http://test.example.com",
        member_id="M123",
    )


class TestNotifyHealth:
    """Test health endpoint"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"


class TestVapidEndpoint:
    """Test VAPID key endpoint"""

    @pytest.mark.asyncio
    async def test_vapid_public_key(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/vapid-public-key")
            assert response.status_code == 200
            data = response.json()
            assert "publicKey" in data
            assert isinstance(data["publicKey"], str)
            assert len(data["publicKey"]) > 0


class TestSubscribeEndpoint:
    """Test subscription management"""

    @pytest.mark.asyncio
    async def test_subscribe_new_user_with_email(
        self, setup_mock_db, mock_subscription
    ):
        db = setup_mock_db
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/subscribe",
                json=mock_subscription.model_dump(),
                params={"email": "test@example.com"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "userId" in data

            # Verify user was created in database
            user = await db.users.find_one({"email": "test@example.com"})
            assert user is not None
            assert len(user["subscriptions"]) == 1
            assert user["subscriptions"][0]["endpoint"] == mock_subscription.endpoint

    @pytest.mark.asyncio
    async def test_subscribe_new_user_with_member_id(
        self, setup_mock_db, mock_subscription
    ):
        db = setup_mock_db
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/subscribe",
                json=mock_subscription.model_dump(),
                params={"member_id": "M123"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "userId" in data

            # Verify user was created with member_id
            user = await db.users.find_one({"member_id": "M123"})
            assert user is not None
            assert user["member_id"] == "M123"

    @pytest.mark.asyncio
    async def test_subscribe_existing_user(self, setup_mock_db, mock_subscription):
        db = setup_mock_db

        # Pre-create user
        await db.users.insert_one(
            {"email": "existing@example.com", "member_id": None, "subscriptions": []}
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/subscribe",
                json=mock_subscription.model_dump(),
                params={"email": "existing@example.com"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True

            # Verify subscription was added
            user = await db.users.find_one({"email": "existing@example.com"})
            assert len(user["subscriptions"]) == 1

    @pytest.mark.asyncio
    async def test_subscribe_duplicate_endpoint(self, setup_mock_db, mock_subscription):
        db = setup_mock_db

        # Pre-create user with existing subscription
        await db.users.insert_one(
            {
                "email": "test@example.com",
                "member_id": None,
                "subscriptions": [mock_subscription.model_dump()],
            }
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/subscribe",
                json=mock_subscription.model_dump(),
                params={"email": "test@example.com"},
            )
            assert response.status_code == 200

            # Verify no duplicate subscription was added
            user = await db.users.find_one({"email": "test@example.com"})
            assert len(user["subscriptions"]) == 1


class TestNotifyEndpoint:
    """Test notification sending functionality"""

    @pytest.mark.asyncio
    async def test_notify_all_users(
        self, setup_mock_db, mock_subscription, mock_notification
    ):
        db = setup_mock_db

        # Setup test users with subscriptions
        await db.users.insert_many(
            [
                {
                    "email": "user1@example.com",
                    "member_id": "M1",
                    "subscriptions": [mock_subscription.model_dump()],
                },
                {
                    "email": "user2@example.com",
                    "member_id": "M2",
                    "subscriptions": [mock_subscription.model_dump()],
                },
            ]
        )

        with patch("notify.app.send_web_push") as mock_send:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                # Create notification without member_id to send to all users
                all_users_notification = NotificationCreate(
                    title="Test Notification",
                    body="This is a test notification",
                    icon="/test-icon.png",
                    url="http://test.example.com",
                )
                response = await ac.post("/notify", json=all_users_notification.model_dump())
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert "notificationId" in data
                assert data["successful"] == 2
                assert data["failed"] == 0

                # Verify web push was called for each subscription
                assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_notify_specific_member(self, setup_mock_db, mock_subscription):
        db = setup_mock_db

        # Setup test users
        await db.users.insert_many(
            [
                {
                    "email": "user1@example.com",
                    "member_id": "M1",
                    "subscriptions": [mock_subscription.model_dump()],
                },
                {
                    "email": "user2@example.com",
                    "member_id": "M2",
                    "subscriptions": [mock_subscription.model_dump()],
                },
            ]
        )

        notification = NotificationCreate(
            title="Member Specific Notification",
            body="This is for member M1 only",
            member_id="M1",
        )

        with patch("notify.app.send_web_push") as mock_send:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post("/notify", json=notification.model_dump())
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert (
                    data["successful"] == 1
                )  # Only one user should receive notification

                # Verify only one web push call was made
                assert mock_send.call_count == 1

    @pytest.mark.asyncio
    async def test_notify_specific_user_id(
        self, setup_mock_db, mock_subscription, mock_notification
    ):
        db = setup_mock_db

        # Setup test user
        user_result = await db.users.insert_one(
            {
                "email": "user@example.com",
                "member_id": "M1",
                "subscriptions": [mock_subscription.model_dump()],
            }
        )
        user_id = str(user_result.inserted_id)

        with patch("notify.app.send_web_push") as mock_send:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/notify",
                    json=mock_notification.model_dump(),
                    params={"user_id": user_id},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert data["successful"] == 1

                assert mock_send.call_count == 1

    @pytest.mark.asyncio
    async def test_notify_invalid_user_id(self, setup_mock_db, mock_notification):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/notify",
                json=mock_notification.model_dump(),
                params={"user_id": "invalid-id"},
            )
            assert response.status_code == 400
            data = response.json()
            assert "Invalid user_id" in data["detail"]

    @pytest.mark.asyncio
    async def test_notify_web_push_failure(
        self, setup_mock_db, mock_subscription, mock_notification
    ):
        db = setup_mock_db

        # Setup test user with matching member_id
        await db.users.insert_one(
            {
                "email": "user@example.com",
                "member_id": "M123",  # Match the mock_notification member_id
                "subscriptions": [mock_subscription.model_dump()],
            }
        )

        # Mock web push to raise exception
        with patch("notify.app.send_web_push") as mock_send:
            mock_send.side_effect = Exception("Push failed")

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post("/notify", json=mock_notification.model_dump())
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert data["successful"] == 0
                assert data["failed"] == 1

                # Verify delivery record was created with failed status
                delivery = await db.deliveries.find_one({"status": "failed"})
                assert delivery is not None
                assert delivery["error"] == "Push failed"

    @pytest.mark.asyncio
    async def test_notify_subscription_removal_on_410(
        self, setup_mock_db, mock_subscription, mock_notification
    ):
        db = setup_mock_db

        # Setup test user with matching member_id
        user_id = await db.users.insert_one(
            {
                "email": "user@example.com",
                "member_id": "M123",  # Match the mock_notification member_id
                "subscriptions": [mock_subscription.model_dump()],
            }
        )

        # Mock web push to return 410 (Gone) response
        mock_exception = Exception("Gone")
        mock_response = Mock()
        mock_response.status_code = 410
        mock_exception.response = mock_response

        with patch("notify.app.send_web_push") as mock_send:
            mock_send.side_effect = mock_exception

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post("/notify", json=mock_notification.model_dump())
                assert response.status_code == 200
                data = response.json()
                assert len(data["removed"]) == 1
                assert mock_subscription.endpoint in data["removed"]

                # Verify subscription was removed from user
                user = await db.users.find_one({"_id": user_id.inserted_id})
                assert len(user["subscriptions"]) == 0

                # Verify delivery record was created with removed status
                delivery = await db.deliveries.find_one({"status": "removed"})
                assert delivery is not None
                assert delivery["status_code"] == 410

    @pytest.mark.asyncio
    async def test_notify_no_users(self, setup_mock_db, mock_notification):
        # Test when no users exist
        with patch("notify.app.send_web_push") as mock_send:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post("/notify", json=mock_notification.model_dump())
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert data["successful"] == 0
                assert data["failed"] == 0

                # Verify no web push calls were made
                assert mock_send.call_count == 0

    @pytest.mark.asyncio
    async def test_notify_stores_notification_record(
        self, setup_mock_db, mock_notification
    ):
        db = setup_mock_db

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/notify",
                json=mock_notification.model_dump(),
                params={"member_id": "M123"},
            )
            assert response.status_code == 200
            data = response.json()

            # Verify notification record was stored
            notification_record = await db.notifications.find_one(
                {"_id": ObjectId(data["notificationId"])}
            )
            assert notification_record is not None
            assert notification_record["title"] == mock_notification.title
            assert notification_record["body"] == mock_notification.body
            assert notification_record["audience"] == "member"
            assert notification_record["member_id"] == "M123"


class TestListEndpoints:
    """Test list endpoints for users, notifications, and deliveries"""

    @pytest.mark.asyncio
    async def test_list_users(self, setup_mock_db, mock_subscription):
        db = setup_mock_db

        # Setup test users
        await db.users.insert_many(
            [
                {
                    "email": "user1@example.com",
                    "member_id": "M1",
                    "subscriptions": [mock_subscription.model_dump()],
                },
                {"email": "user2@example.com", "member_id": "M2", "subscriptions": []},
            ]
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/users")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert any(user["email"] == "user1@example.com" for user in data)
            assert any(user["email"] == "user2@example.com" for user in data)

    @pytest.mark.asyncio
    async def test_list_notifications(self, setup_mock_db):
        db = setup_mock_db

        # Setup test notifications
        await db.notifications.insert_many(
            [
                {
                    "title": "Test 1",
                    "body": "Body 1",
                    "audience": "all",
                    "member_id": None,
                },
                {
                    "title": "Test 2",
                    "body": "Body 2",
                    "audience": "member",
                    "member_id": "M1",
                },
            ]
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/notifications")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert any(notif["title"] == "Test 1" for notif in data)
            assert any(notif["title"] == "Test 2" for notif in data)

    @pytest.mark.asyncio
    async def test_list_deliveries(self, setup_mock_db):
        db = setup_mock_db

        # Setup test deliveries
        current_time = datetime.utcnow().isoformat()
        await db.deliveries.insert_many(
            [
                {
                    "notification_id": str(ObjectId()),
                    "user_id": str(ObjectId()),
                    "endpoint": "https://example.com/1",
                    "status": "sent",
                    "created_at": current_time,
                },
                {
                    "notification_id": str(ObjectId()),
                    "user_id": str(ObjectId()),
                    "endpoint": "https://example.com/2",
                    "status": "failed",
                    "status_code": 400,
                    "error": "Bad request",
                    "created_at": current_time,
                },
            ]
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/deliveries")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert any(delivery["status"] == "sent" for delivery in data)
            assert any(delivery["status"] == "failed" for delivery in data)


class TestNotificationIntegration:
    """Integration tests for notification workflow"""

    @pytest.mark.asyncio
    async def test_full_notification_workflow(self, setup_mock_db, mock_subscription):
        # The fixture is already yielded, so we can use it directly
        # Note: setup_mock_db returns the MockDatabase instance

        # Step 1: Subscribe user
        async with AsyncClient(app=app, base_url="http://test") as ac:
            subscribe_response = await ac.post(
                "/subscribe",
                json=mock_subscription.model_dump(),
                params={"member_id": "M123"},
            )
            assert subscribe_response.status_code == 200

            # Step 2: Send notification
            notification = NotificationCreate(
                title="Integration Test", body="Testing full workflow", member_id="M123"
            )

            with patch("notify.app.send_web_push") as mock_send:
                notify_response = await ac.post(
                    "/notify", json=notification.model_dump()
                )
                assert notify_response.status_code == 200
                notify_data = notify_response.json()
                assert notify_data["successful"] == 1

                # Step 3: Verify records were created
                notification_id = notify_data["notificationId"]

                # Check notification record
                notification_record = await setup_mock_db.notifications.find_one(
                    {"_id": ObjectId(notification_id)}
                )
                assert notification_record is not None

                # Check delivery record
                delivery_record = await setup_mock_db.deliveries.find_one(
                    {"notification_id": notification_id}
                )
                assert delivery_record is not None
                assert delivery_record["status"] == "sent"

                # Verify web push was called with correct payload
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                # call_args[0] contains positional arguments: [subscription, payload]
                push_payload = call_args[0][1]
                assert push_payload["title"] == "Integration Test"
                assert push_payload["body"] == "Testing full workflow"
