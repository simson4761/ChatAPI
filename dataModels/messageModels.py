from enum import Enum
from pydantic import BaseModel


class MessageType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    FILE = "FILE"
    LOCATION = "LOCATION"
    SYSTEM = "SYSTEM"


class MessageStatus(str, Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    SEEN = "SEEN"
    FAILED = "FAILED"


class ChatMessage(BaseModel):
    id: str
    thread_id: str
    user_id: str
    text: str
    type: MessageType = MessageType.TEXT
    timestamp: int  # epoch milliseconds
    status: MessageStatus = MessageStatus.SENT

