from enum import Enum
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from rental_core.db import Base


class MaintenanceStatus(str, Enum):
    pending = "pending"
    open = "open"
    in_progress = "in_progress"
    closed = "closed"

class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="CASCADE"), nullable=False)
    description = Column(String, nullable=False)
    priority = Column(String, nullable=False, default="low")
    status = Column(String, nullable=False, default=MaintenanceStatus.open.value)

    assigned_to = Column(String, nullable=True, default="")
    contractor_id = Column(Integer, ForeignKey("contractors.id", ondelete="SET NULL"), nullable=True)
    photo_path = Column(String, nullable=True)
    closed_date = Column(Date, nullable=True)

    request_date = Column(Date, nullable=False)
    unit = relationship("Unit")
    contractor = relationship("Contractor", back_populates="maintenance_requests")
