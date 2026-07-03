from core.database import Base
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String


class Whatsapp_settings(Base):
    __tablename__ = "whatsapp_settings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    setting_key = Column(String, nullable=False)
    setting_value = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)