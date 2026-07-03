from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String


class Offers(Base):
    __tablename__ = "offers"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    code = Column(String, nullable=True)
    supplier_id = Column(Integer, nullable=True)
    title = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    model = Column(String, nullable=True)
    version = Column(String, nullable=True)
    year = Column(String, nullable=True)
    color = Column(String, nullable=True)
    mileage = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    supplier_price = Column(Float, nullable=True)
    description = Column(String, nullable=True)
    status = Column(String, nullable=True, default='pending', server_default='pending')
    negotiation_status = Column(String, nullable=True, default='awaiting_update', server_default='awaiting_update')
    negotiation_substatus = Column(String, nullable=True, default='none', server_default='none')
    negotiation_buyer_id = Column(Integer, nullable=True)
    doc_status = Column(String, nullable=True, default='none', server_default='none')
    vehicle_status = Column(String, nullable=True, default='none', server_default='none')
    negotiation_deadline_hours = Column(Integer, nullable=True, default=48, server_default='48')
    distributed_at = Column(String, nullable=True)
    finalized_at = Column(String, nullable=True)
    images = Column(String, nullable=True)
    selected_images = Column(String, nullable=True)
    fipe = Column(String, nullable=True)
    plate = Column(String, nullable=True)
    fuel = Column(String, nullable=True)
    transmission = Column(String, nullable=True)
    suggested_category = Column(String, nullable=True)
    has_manual = Column(Boolean, nullable=True, default=False, server_default='false')
    has_spare_key = Column(Boolean, nullable=True, default=False, server_default='false')
    is_auction = Column(Boolean, nullable=True, default=False, server_default='false')
    target_categories = Column(String, nullable=True)
    processed_images = Column(String, nullable=True)
    original_images = Column(String, nullable=True)
    sold_buyer_id = Column(Integer, nullable=True)
    sale_notes = Column(String, nullable=True)
    vehicle_dossier_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)