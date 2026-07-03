from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String


class Vehicle_dossier_access(Base):
    __tablename__ = "vehicle_dossier_access"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    dossier_id = Column(Integer, nullable=False, index=True)
    buyer_id = Column(Integer, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    can_view_consultations = Column(Boolean, nullable=True, default=True, server_default="true")
    can_view_files = Column(Boolean, nullable=True, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
