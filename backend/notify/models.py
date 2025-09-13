from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscription(BaseModel):
    endpoint: str
    keys: SubscriptionKeys


class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: Optional[str] = None
    name: Optional[str] = None
    member_id: Optional[str] = None  # Added for healthcare claims targeting
    subscriptions: List[PushSubscription] = Field(default_factory=list)


class NotificationCreate(BaseModel):
    title: str
    body: str
    icon: Optional[str] = None
    url: Optional[str] = None
    member_id: Optional[str] = None  # Added for healthcare claims targeting


class NotificationRecord(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    body: str
    icon: Optional[str] = None
    url: Optional[str] = None
    audience: Literal["all", "user", "member"] = "all"
    user_id: Optional[str] = None
    member_id: Optional[str] = None


class DeliveryRecord(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    notification_id: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    status: Literal["sent", "failed", "removed"]
    status_code: Optional[int] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
