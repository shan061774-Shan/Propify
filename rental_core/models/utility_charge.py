from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from rental_core.db import Base


class UtilityCharge(Base):
    __tablename__ = "utility_charges"

    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("leases.id", ondelete="CASCADE"), nullable=False)
    utility_type = Column(String, nullable=False, default="other")
    description = Column(String, nullable=True, default="")
    amount = Column(Float, nullable=False)
    bill_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    is_paid = Column(Boolean, nullable=False, default=False)
    paid_payment_id = Column(Integer, ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)

    lease = relationship("Lease", back_populates="utility_charges")
