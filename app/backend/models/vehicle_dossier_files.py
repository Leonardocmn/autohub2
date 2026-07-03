from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String


class Vehicle_dossier_files(Base):
    __tablename__ = "vehicle_dossier_files"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    dossier_id = Column(Integer, nullable=False, index=True)
    offer_id = Column(Integer, nullable=True, index=True)
    plate = Column(String, nullable=False, index=True)
    file_type = Column(String, nullable=False, default="document", server_default="document")
    file_name = Column(String, nullable=True)
    storage_bucket = Column(String, nullable=True)
    storage_key = Column(String, nullable=True)
    public_url = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    uploaded_by_user_id = Column(String, nullable=True)
    is_admin_only = Column(Boolean, nullable=True, default=True, server_default="true")
    is_released_to_buyer = Column(Boolean, nullable=True, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
