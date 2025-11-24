"""
Association tables for many-to-many relationships.
Kept separate to avoid circular imports between models.
"""
from sqlalchemy import Column, Integer, Table, ForeignKey
from app.models.base import Base

user_household = Table(
    'user_household',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('household_id', Integer, ForeignKey('households.id', ondelete='CASCADE'), primary_key=True)
)