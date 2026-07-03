from core.database import Base
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String


class Whatsapp_admin_sessions(Base):
    __tablename__ = "whatsapp_admin_sessions"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_phone = Column(String, nullable=False, unique=True)
    state = Column(String, nullable=True, default='idle', server_default='idle')
    temp_data = Column(String, nullable=True)
    menu_path = Column(String, nullable=True, default='main', server_default='main')
    menu_data = Column(String, nullable=True)
    last_interaction_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)