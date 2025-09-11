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
    subscriptions: List[PushSubscription] = Field(default_factory=list)


class NotificationCreate(BaseModel):
    title: str
    body: str
    icon: Optional[str] = None
    url: Optional[str] = None


class NotificationRecord(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    body: str
    icon: Optional[str] = None
    url: Optional[str] = None
    audience: Literal["all", "user"] = "all"
    user_id: Optional[str] = None

