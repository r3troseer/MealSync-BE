"""
Association tables for many-to-many relationships.
Kept separate to avoid circular imports between models.
"""
from sqlalchemy import Column, Integer, Table, ForeignKey, String, DateTime, func
from app.models.base import Base

user_household = Table(
    'user_household',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('household_id', Integer, ForeignKey('households.id', ondelete='CASCADE'), primary_key=True),
    Column('role', String(20), nullable=False, server_default='member'),  # 'admin' or 'member'
    Column('joined_at', DateTime(timezone=True), server_default=func.now(), nullable=False)
)