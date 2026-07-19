"""Maintenance models."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from sqlalchemy.sql import func
from app.database import Base


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"

    id = Column(Integer, primary_key=True, index=True)
    equipment_tag = Column(String(100), nullable=False)
    task_type = Column(String(50), nullable=False)  # preventive, corrective, predictive
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")
    status = Column(String(50), default="pending")
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SparePart(Base):
    __tablename__ = "spare_parts"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    equipment_tags = Column(JSON, default=list)
    quantity = Column(Integer, default=0)
    min_quantity = Column(Integer, default=0)
    location = Column(String(255), nullable=True)
    cost = Column(Float, nullable=True)
    lead_time_days = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RootCauseAnalysis(Base):
    __tablename__ = "root_cause_analyses"

    id = Column(Integer, primary_key=True, index=True)
    equipment_tag = Column(String(100), nullable=False)
    failure_mode = Column(String(255), nullable=False)
    symptoms = Column(JSON, default=list)
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    contributing_factors = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
