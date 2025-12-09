from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.household import (
    HouseholdCreate,
    HouseholdUpdate,
    HouseholdResponse,
    HouseholdJoinRequest,
    InviteCodeResponse,
    HouseholdMemberResponse,
    PromoteMemberRequest
)
from app.schemas.result import Result
from app.services.household_service import HouseholdService

router = APIRouter()


@router.post("", response_model=Result[HouseholdResponse], status_code=status.HTTP_201_CREATED)
async def create_household(
    household_data: HouseholdCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new household with current user as admin."""
    service = HouseholdService(db)
    household = service.create_household(current_user.id, household_data)
    return Result.successful(data=household)


@router.get("", response_model=Result[List[HouseholdResponse]])
async def get_my_households(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all households the current user belongs to."""
    service = HouseholdService(db)
    households = service.get_user_households(current_user.id)
    return Result.successful(data=households)


@router.get("/{household_id}", response_model=Result[HouseholdResponse])
async def get_household(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get household details."""
    service = HouseholdService(db)
    household = service.get_household(household_id, current_user.id)
    return Result.successful(data=household)


@router.put("/{household_id}", response_model=Result[HouseholdResponse])
async def update_household(
    household_id: int,
    household_data: HouseholdUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update household details (admin only)."""
    service = HouseholdService(db)
    household = service.update_household(household_id, current_user.id, household_data)
    return Result.successful(data=household)


@router.delete("/{household_id}", response_model=Result[dict])
async def delete_household(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete household (admin only)."""
    service = HouseholdService(db)
    service.delete_household(household_id, current_user.id)
    return Result.successful(data={"message": "Household deleted successfully"})


@router.post("/join", response_model=Result[HouseholdResponse])
async def join_household(
    join_data: HouseholdJoinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a household using an invite code."""
    service = HouseholdService(db)
    household = service.join_household(current_user.id, join_data.invite_code)
    return Result.successful(data=household)


@router.post("/{household_id}/leave", response_model=Result[dict])
async def leave_household(
    household_id: int,
    promotion_data: Optional[PromoteMemberRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Leave a household. If last admin, must promote another member or household will be deleted."""
    service = HouseholdService(db)
    new_admin_id = promotion_data.new_admin_id if promotion_data else None
    result = service.leave_household(household_id, current_user.id, new_admin_id)
    return Result.successful(data=result)


@router.get("/{household_id}/members", response_model=Result[List[HouseholdMemberResponse]])
async def get_members(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all household members."""
    service = HouseholdService(db)
    members = service.get_members(household_id, current_user.id)
    return Result.successful(data=members)


@router.post("/{household_id}/invite", response_model=Result[InviteCodeResponse])
async def regenerate_invite(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new invite code for the household (admin only)."""
    service = HouseholdService(db)
    new_code = service.regenerate_invite_code(household_id, current_user.id)
    return Result.successful(data={"invite_code": new_code})


@router.delete("/{household_id}/members/{user_id}", response_model=Result[dict])
async def remove_member(
    household_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a member from the household (admin only)."""
    service = HouseholdService(db)
    result = service.remove_member(household_id, current_user.id, user_id)
    return Result.successful(data=result)
