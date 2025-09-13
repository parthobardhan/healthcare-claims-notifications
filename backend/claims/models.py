from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date


class ClaimStatus(str, Enum):
    submitted = "submitted"
    pending = "pending"
    adjudicated = "adjudicated"
    paid = "paid"
    denied = "denied"


class ClaimBase(BaseModel):
    member_id: str = Field(..., description="Member identifier")
    provider_id: str = Field(..., description="Provider identifier")
    service_date: date = Field(..., description="Date of service")
    received_date: date = Field(..., description="Date claim was received")
    diagnosis_codes: List[str] = Field(default_factory=list)
    procedure_codes: List[str] = Field(default_factory=list)
    amount_billed: float = Field(..., ge=0)
    amount_allowed: float = Field(0, ge=0)
    amount_paid: float = Field(0, ge=0)
    status: ClaimStatus = Field(default=ClaimStatus.submitted)
    notes: Optional[str] = None


class ClaimCreate(ClaimBase):
    pass


class ClaimUpdate(BaseModel):
    member_id: Optional[str] = None
    provider_id: Optional[str] = None
    service_date: Optional[date] = None
    received_date: Optional[date] = None
    diagnosis_codes: Optional[List[str]] = None
    procedure_codes: Optional[List[str]] = None
    amount_billed: Optional[float] = Field(None, ge=0)
    amount_allowed: Optional[float] = Field(None, ge=0)
    amount_paid: Optional[float] = Field(None, ge=0)
    status: Optional[ClaimStatus] = None
    notes: Optional[str] = None


class ClaimOut(ClaimBase):
    id: str = Field(..., description="Claim identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "64f9c2e4b3f5c1a2b4d6e7f8",
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
                "notes": "Initial submission",
            }
        }
