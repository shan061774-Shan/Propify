from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from rental_core.db import Base


class OwnerAdmin(Base):
    __tablename__ = "owner_admins"
    __table_args__ = (UniqueConstraint("owner_id", "phone", name="uq_owner_admin_phone"),)

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owner_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    phone = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True, default="")
    email = Column(String, nullable=True, default="")
    password_hash = Column(String, nullable=True, default="")
    password_salt = Column(String, nullable=True, default="")
    status = Column(String, nullable=False, default="invited", index=True)
    invited_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    owner = relationship("OwnerAccount", back_populates="admins")