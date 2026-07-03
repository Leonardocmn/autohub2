from models.base import BaseModel
from sqlalchemy import Column, String, Text


class Fipe_consultation_logs(BaseModel):
    __tablename__ = "fipe_consultation_logs"
    __table_args__ = {"extend_existing": True}

    phone = Column(String(20), nullable=False, index=True)
    plate = Column(String(10), nullable=True, index=True)
    fipe_code = Column(String(20), nullable=True)
    vehicle_description = Column(String(300), nullable=True)
    price_returned = Column(String(50), nullable=True)
    source = Column(String(30), nullable=False, default="admin")
    user_id = Column(String(100), nullable=True)
    result_json = Column(Text, nullable=True)