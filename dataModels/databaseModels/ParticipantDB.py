from sqlalchemy import Column, String, BIGINT
from dataModels.databaseModels.Base import Base


class ParticipantDB(Base):
    __tablename__ = "participants"

    user_id = Column(String, primary_key=True)
    name = Column(String)
    phone = Column(String)
    password = Column(String)
    avatar_url = Column(String)
    last_seen = Column(BIGINT)
