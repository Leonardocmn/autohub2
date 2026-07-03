from core.database import Base
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String


class Vehicle_dossiers(Base):
    __tablename__ = "vehicle_dossiers"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    plate = Column(String, nullable=False, index=True)
    offer_id = Column(Integer, nullable=True, index=True)
    sold_buyer_id = Column(Integer, nullable=True, index=True)
    status = Column(String, nullable=True, default="active", server_default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
