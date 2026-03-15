import uuid
from enum import Enum

from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship

from rental_core.db import Base


class LeaseStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    transferred = "transferred"
    terminated = "terminated"


class Lease(Base):
    __tablename__ = "leases"

    id = Column(Integer, primary_key=True, index=True)
    lease_number = Column(String, unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4())[:8])

    unit_id = Column(Integer, ForeignKey("units.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(String, nullable=False, default=LeaseStatus.active.value)

    unit = relationship("Unit", back_populates="leases")
    tenant = relationship("Tenant", back_populates="leases")
    payments = relationship("Payment", back_populates="lease", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="lease", cascade="all, delete-orphan")
    utility_charges = relationship("UtilityCharge", back_populates="lease", cascade="all, delete-orphan")
