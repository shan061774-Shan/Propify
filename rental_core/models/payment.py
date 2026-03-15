from sqlalchemy import Column, Integer, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from rental_core.db import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    lease_id = Column(Integer, ForeignKey("leases.id", ondelete="CASCADE"), nullable=False)

    lease = relationship("Lease", back_populates="payments")
