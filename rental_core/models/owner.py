from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from rental_core.db import Base


class OwnerAccount(Base):
    __tablename__ = "owner_accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    password_salt = Column(String, nullable=False)

    company_name = Column(String, nullable=False, default="")
    company_address = Column(String, nullable=True, default="")
    company_phone = Column(String, nullable=True, default="")

    owner_name = Column(String, nullable=False, default="")
    owner_email = Column(String, nullable=True, default="")
    owner_phone = Column(String, nullable=True, default="")
    two_fa_enabled = Column(Boolean, nullable=False, default=False)
    is_blocked = Column(Boolean, nullable=False, default=False)
    blocked_at = Column(DateTime, nullable=True)
    blocked_reason = Column(String, nullable=True, default="")

    properties = relationship("Property", back_populates="owner")
    admins = relationship("OwnerAdmin", back_populates="owner", cascade="all, delete-orphan")
    password_resets = relationship("OwnerPasswordReset", back_populates="owner", cascade="all, delete-orphan")
