from core.database import Base
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String


class Buyers(Base):
    __tablename__ = "buyers"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    company = Column(String, nullable=True)
    city = Column(String, nullable=True)
    observations = Column(String, nullable=True)
    status = Column(String, nullable=True, default='active', server_default='active')
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)