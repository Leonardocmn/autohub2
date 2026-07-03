from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String


class Whatsapp_messages(Base):
    __tablename__ = "whatsapp_messages"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    phone = Column(String, nullable=False)
    contact_name = Column(String, nullable=True)
    direction = Column(String, nullable=False)
    message_type = Column(String, nullable=True)
    content = Column(String, nullable=True)
    media_url = Column(String, nullable=True)
    message_id = Column(String, nullable=True)
    conversation_id = Column(Integer, nullable=True)
    processed = Column(Boolean, nullable=True, default=False, server_default='false')
    is_supplier = Column(Boolean, nullable=True, default=False, server_default='false')
    is_buyer = Column(Boolean, nullable=True, default=False, server_default='false')
    timestamp = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)