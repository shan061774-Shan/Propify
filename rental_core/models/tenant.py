from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from rental_core.db import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True, default="")
    phone = Column(String, nullable=True, default="")

    leases = relationship("Lease", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")

