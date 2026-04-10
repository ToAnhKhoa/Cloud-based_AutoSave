from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class GamePathCache(Base):
    __tablename__ = "game_path_cache"

    id = Column(Integer, primary_key=True, index=True)
    official_name = Column(String, unique=True, index=True, nullable=False)
    default_path = Column(String, nullable=False)
    
    aliases = relationship("GameAlias", back_populates="game")

class GameAlias(Base):
    __tablename__ = "game_alias"

    id = Column(Integer, primary_key=True, index=True)
    user_input = Column(String, unique=True, index=True, nullable=False)
    game_id = Column(Integer, ForeignKey("game_path_cache.id"), nullable=False)
    
    game = relationship("GamePathCache", back_populates="aliases")
