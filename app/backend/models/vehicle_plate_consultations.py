from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text


class Vehicle_plate_consultations(Base):
    __tablename__ = "vehicle_plate_consultations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    plate = Column(String, nullable=False, index=True)
    offer_id = Column(Integer, nullable=True, index=True)
    dossier_id = Column(Integer, nullable=True, index=True)
    requested_by_user_id = Column(String, nullable=True, index=True)
    requested_by_role = Column(String, nullable=True)
    source = Column(String, nullable=True)
    success = Column(Boolean, nullable=True, default=False, server_default="false")
    result_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
