from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.v1.generics import GenericModel

T = TypeVar("T")


class Participant(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str
    name: str
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    is_online: bool = Field(default=False, alias="isOnline")
    last_seen: int | None = Field(default=None, alias="lastSeen")
    # epoch milliseconds, relevant when isOnline == false


class Conversation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    thread_id: str = Field(alias="threadId")
    display_name: str = Field(alias="displayName")
    last_message_id: str | None = Field(default=None, alias="lastMessageId")
    unread_count: int = Field(alias="unreadCount")


class ApiResponse(GenericModel, Generic[T]):
    success: bool
    responseCode: int
    responseMessage: str
    data: T | None = None
    error: str | None = None
