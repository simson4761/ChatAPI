from sqlalchemy import Column, String, ForeignKey, CheckConstraint, Index, UniqueConstraint, \
    ForeignKeyConstraint, BIGINT

from dataModels.databaseModels.Base import Base


class ChatMessageDB(Base):
    __tablename__ = "messages"

    chat_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("participants.user_id"))
    thread_id = Column(String, ForeignKey("conversations.thread_id"))
    text = Column(String)
    type = Column(String)
    timestamp = Column(BIGINT)
    status = Column(String)

    __table_args__ = (
        # 1. Composite/multi-column foreign key
        ForeignKeyConstraint(
            ["user_id", "thread_id"],
            ["conversation_participants.user_id", "conversation_participants.thread_id"],
        ),

        # 2. Composite unique constraint (e.g. no duplicate chat_id per user)
        UniqueConstraint("user_id", "chat_id", name="uq_user_chat"),

        # 3. Multi-column index (for fast lookups by thread)
        Index("ix_user_thread", "user_id", "thread_id"),

        # 4. Check constraint (row-level validation)
        CheckConstraint("timestamp > 0", name="ck_positive_timestamp"),

        # 5. Table-level options (engine, schema, etc.)
        {"sqlite_autoincrement": True},
    )
