from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from rental_core.db import Base


class OwnerPasswordReset(Base):
    __tablename__ = "owner_password_resets"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owner_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    owner = relationship("OwnerAccount", back_populates="password_resets")
