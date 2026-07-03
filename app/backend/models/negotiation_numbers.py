from core.database import Base
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String


class Negotiation_numbers(Base):
    __tablename__ = "negotiation_numbers"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    phone = Column(String, nullable=False)
    responsible_name = Column(String, nullable=False)
    status = Column(String, nullable=True, default='active', server_default='active')
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)