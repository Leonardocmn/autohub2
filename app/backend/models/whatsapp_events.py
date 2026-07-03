from core.database import Base
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String


class Whatsapp_events(Base):
    __tablename__ = "whatsapp_events"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    event_type = Column(String, nullable=True)
    instance = Column(String, nullable=True)
    sender_phone = Column(String, nullable=True)
    raw_data = Column(String, nullable=True)
    processed = Column(String, nullable=True, default='pending', server_default='pending')
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)