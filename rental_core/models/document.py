from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from rental_core.db import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False, unique=True)
    content_type = Column(String, nullable=True, default="application/octet-stream")
    document_type = Column(String, nullable=True, default="other")
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    lease_id = Column(Integer, ForeignKey("leases.id", ondelete="CASCADE"), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)

    lease = relationship("Lease", back_populates="documents")
    tenant = relationship("Tenant", back_populates="documents")
