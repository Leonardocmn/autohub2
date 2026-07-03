from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String


class Whatsapp_conversations(Base):
    __tablename__ = "whatsapp_conversations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    supplier_phone = Column(String, nullable=False)
    supplier_name = Column(String, nullable=True)
    status = Column(String, nullable=True, default='active', server_default='active')
    offer_draft_id = Column(Integer, nullable=True)
    last_message_at = Column(String, nullable=True)
    message_count = Column(Integer, nullable=True, default=0, server_default='0')
    ai_analysis = Column(String, nullable=True)
    window_closed = Column(Boolean, nullable=True, default=False, server_default='false')
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)