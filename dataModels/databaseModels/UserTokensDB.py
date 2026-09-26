from sqlalchemy import Column, String, ForeignKey, BIGINT

from dataModels.databaseModels.Base import Base


class UserTokensDB(Base):
    __tablename__ = "user_tokens"

    user_id = Column(String, ForeignKey("participants.user_id"), primary_key=True)
    user_name = Column(String)
    access_token = Column(String)
    refresh_token = Column(String)
    user_platform = Column(String)
    fcm_token = Column(String)
    expires_at = Column(BIGINT)
