from sqlalchemy import Column, Float, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from rental_core.db import Base

class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    unit_number = Column(String, nullable=False)
    description = Column(String, nullable=True)
    rent_amount = Column(Float, nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    property = relationship("Property", back_populates="units")
    leases = relationship("Lease", back_populates="unit", cascade="all, delete-orphan")
    maintenance_requests = relationship("MaintenanceRequest", back_populates="unit", cascade="all, delete-orphan")
