from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from dataModels.databaseModels.Base import Base


class ConversationParticipantsDB(Base):
    __tablename__ = "conversation_participants"

    thread_id = Column(String, ForeignKey("conversations.thread_id"), primary_key=True)
    user_id = Column(String, ForeignKey("participants.user_id"), primary_key=True)

    conversation = relationship("ConversationDB", foreign_keys=[thread_id], back_populates="participants")
    participant = relationship("ParticipantDB", foreign_keys=[user_id])
