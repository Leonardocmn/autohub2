from core.database import Base
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer


class Buyer_categories(Base):
    __tablename__ = "buyer_categories"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    buyer_id = Column(Integer, nullable=False)
    category_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)