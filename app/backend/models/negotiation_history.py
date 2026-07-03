from core.database import Base
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String


class Negotiation_history(Base):
    __tablename__ = "negotiation_history"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    offer_id = Column(Integer, nullable=False)
    admin_name = Column(String, nullable=True)
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    buyer_id = Column(Integer, nullable=True)
    observations = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)