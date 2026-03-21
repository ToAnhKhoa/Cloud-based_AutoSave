from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class AppData(Base):
    __tablename__ = "app_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    app_name = Column(String, index=True, nullable=False)
    cloud_path = Column(String, nullable=False)
    checksum = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship to User
    owner = relationship("User", back_populates="app_data")
