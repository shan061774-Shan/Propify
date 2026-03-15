from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from rental_core.db import Base


class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True, default="")
    email = Column(String, nullable=True, default="")
    specialty = Column(String, nullable=True, default="")
    notes = Column(String, nullable=True, default="")

    maintenance_requests = relationship("MaintenanceRequest", back_populates="contractor")
