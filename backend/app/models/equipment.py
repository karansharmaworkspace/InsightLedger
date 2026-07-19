"""Equipment models."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    tag = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    equipment_type = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    specifications = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EquipmentRelationship(Base):
    __tablename__ = "equipment_relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_tag = Column(String(100), ForeignKey("equipment.tag"), nullable=False)
    target_tag = Column(String(100), ForeignKey("equipment.tag"), nullable=False)
    relationship_type = Column(String(100), nullable=False)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
