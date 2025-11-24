from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    dietary_preferences: Optional[str] = None
    allergies: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    dietary_preferences: Optional[str] = None
    allergies: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    id: int
    uuid: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None  # Optional refresh token


class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None