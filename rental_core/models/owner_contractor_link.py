from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from rental_core.db import Base


class OwnerContractorLink(Base):
    __tablename__ = "owner_contractor_links"
    __table_args__ = (UniqueConstraint("owner_id", "phone", name="uq_owner_contractor_phone"),)

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owner_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    contractor_id = Column(Integer, ForeignKey("contractors.id", ondelete="SET NULL"), nullable=True, index=True)
    phone = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="invited", index=True)
    invited_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    owner = relationship("OwnerAccount")
    contractor = relationship("Contractor")
