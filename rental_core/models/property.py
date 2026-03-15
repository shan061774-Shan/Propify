from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from rental_core.db import Base

class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    grace_period_days = Column(Integer, nullable=False, default=3)
    late_fee_amount = Column(Integer, nullable=False, default=30)
    owner_id = Column(Integer, ForeignKey("owner_accounts.id", ondelete="CASCADE"), nullable=True, index=True)
    units = relationship("Unit", back_populates="property", cascade="all, delete-orphan")
    owner = relationship("OwnerAccount", back_populates="properties")