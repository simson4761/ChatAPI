from sqlalchemy import Column, String, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from dataModels.databaseModels.Base import Base


class ConversationDB(Base):
    __tablename__ = "conversations"

    thread_id = Column(String, primary_key=True)
    display_name = Column(String)
    last_message_id = Column(String)
    unread_count = Column(Integer)

    participants = relationship("ConversationParticipantsDB", back_populates="conversation")

    __table_args__ = (
        UniqueConstraint("thread_id"),
    )
