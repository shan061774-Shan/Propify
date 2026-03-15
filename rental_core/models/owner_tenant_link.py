from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from rental_core.db import Base


class OwnerTenantLink(Base):
    __tablename__ = "owner_tenant_links"
    __table_args__ = (UniqueConstraint("owner_id", "phone", name="uq_owner_tenant_phone"),)

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owner_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    phone = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="invited", index=True)
    invited_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    owner = relationship("OwnerAccount")
    tenant = relationship("Tenant")
