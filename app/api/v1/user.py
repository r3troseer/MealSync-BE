from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from ...database import get_db
from ...dependencies import get_current_user
from app.models.user import User
from ...schemas.user import UserResponse, UserUpdate, PasswordChange
from ...schemas.result import Result
from ...services.userService import UserService
from ...core.exception import ResourceNotFoundException

router = APIRouter()


@router.get("/me", response_model=Result[UserResponse])
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user's profile.

    Returns:
        Result[UserResponse]: Success result with user profile data
    """
    return Result.successful(data=current_user)


@router.put("/me", response_model=Result[UserResponse])
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current user's profile.

    Only provided fields will be updated.

    Returns:
        Result[UserResponse]: Success result with updated user data
    """
    user_service = UserService(db)
    updated_user = user_service.update_user(current_user.id, user_update)
    return Result.successful(data=updated_user)


@router.delete("/me", response_model=Result[dict], status_code=status.HTTP_200_OK)
async def delete_my_account(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Delete current user's account.

    This action is permanent and cannot be undone.

    Returns:
        Result[dict]: Success result with deletion confirmation
    """
    user_service = UserService(db)
    user_service.delete_user(current_user.id)
    return Result.successful(data={"message": "Account deleted successfully"})


@router.post("/me/change-password", response_model=Result[UserResponse])
async def change_my_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change current user's password.

    Requires old password for verification.

    Returns:
        Result[UserResponse]: Success result with updated user data
    """
    user_service = UserService(db)
    updated_user = user_service.change_password(
        current_user.id, password_data.old_password, password_data.new_password
    )
    return Result.successful(data=updated_user)


@router.post("/me/deactivate", response_model=Result[UserResponse])
async def deactivate_my_account(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Deactivate current user's account.

    Account can be reactivated by contacting support.

    Returns:
        Result[UserResponse]: Success result with deactivated user data
    """
    user_service = UserService(db)
    deactivated_user = user_service.deactivate_account(current_user.id)
    return Result.successful(data=deactivated_user)


@router.get("/{user_id}", response_model=Result[UserResponse])
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get user by ID.

    Users can only view profiles of members in their shared households.

    Returns:
        Result[UserResponse]: Success result with user data
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)

    if not user:
        raise ResourceNotFoundException("User", user_id)

    # Check if users share any household (implement after household model is ready)
    # For now, allow viewing any user
    # TODO: Add household permission check

    return Result.successful(data=user)


@router.get("/", response_model=Result[List[UserResponse]])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all users (paginated).

    This endpoint might be restricted to admins in production.

    Returns:
        Result[List[UserResponse]]: Success result with list of users
    """
    user_service = UserService(db)
    users = user_service.get_all_users(skip=skip, limit=limit)
    return Result.successful(data=users)
