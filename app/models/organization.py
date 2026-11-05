"""Organization multi-tenant model."""
from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimeStampedModel


class Organization(Base, TimeStampedModel):
    __tablename__ = "organizations"

    name = Column(String(150), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    jurisdiction = Column(String(100), nullable=True)  # e.g., "State Law Enforcement", "Judiciary"

    departments = relationship("Department", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
