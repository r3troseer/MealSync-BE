from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class HouseholdBase(BaseModel):
    """Base household schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Household name")
    description: Optional[str] = Field(None, max_length=500, description="Household description")


class HouseholdCreate(HouseholdBase):
    """Schema for creating a new household."""
    pass


class HouseholdUpdate(BaseModel):
    """Schema for updating household details."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class HouseholdJoinRequest(BaseModel):
    """Schema for joining a household via invite code."""
    invite_code: str = Field(..., min_length=8, max_length=20, description="Household invite code")


class InviteCodeResponse(BaseModel):
    """Schema for invite code response."""
    invite_code: str


class HouseholdMemberResponse(BaseModel):
    """Schema for household member information."""
    user_id: int
    uuid: str
    username: str
    full_name: Optional[str]
    email: str
    role: str = Field(..., description="Member role: 'admin' or 'member'")
    joined_at: datetime

    class Config:
        from_attributes = True


class HouseholdResponse(HouseholdBase):
    """Schema for household response."""
    id: int
    uuid: str
    invite_code: str
    created_by_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    member_count: Optional[int] = None
    members: Optional[List[HouseholdMemberResponse]] = None

    class Config:
        from_attributes = True


class PromoteMemberRequest(BaseModel):
    """Schema for promoting a member to admin when leaving."""
    new_admin_id: int = Field(..., description="User ID of member to promote to admin")
