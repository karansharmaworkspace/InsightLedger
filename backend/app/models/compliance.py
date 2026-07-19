"""Compliance models."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id = Column(Integer, primary_key=True, index=True)
    standard = Column(String(100), nullable=False)  # ISA-5.1, OSHA, EPA
    section = Column(String(100), nullable=False)
    requirement = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, compliant, non_compliant, na
    evidence = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    equipment_tags = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    source_document_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
