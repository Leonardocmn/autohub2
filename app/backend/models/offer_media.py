from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String


class Offer_media(Base):
    __tablename__ = "offer_media"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    offer_id = Column(Integer, nullable=True)
    url = Column(String, nullable=True)
    processed_url = Column(String, nullable=True)
    media_type = Column(String, nullable=True, default='image', server_default='image')
    position = Column(Integer, nullable=True, default=0, server_default='0')
    is_selected = Column(Boolean, nullable=True, default=False, server_default='false')
    caption = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)