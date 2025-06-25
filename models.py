from sqlalchemy import Column, Integer, String, Boolean
from database import Base
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.mutable import MutableDict

class Bird(Base):
    __tablename__ = "birds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    last_seen = Column(Integer)
    currently_observed = Column(Boolean, index=True)
    hourly_observations = Column(MutableDict.as_mutable(JSON), default=dict)