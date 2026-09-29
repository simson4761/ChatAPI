from typing import Optional

from pydantic import BaseModel

from dataModels.conversationModels import Conversation
from dataModels.messageModels import MessageType, MessageStatus


class CreateConversationRequest(BaseModel):
    created_at: str
    conversation: Conversation
    participant_id: str


class NewMessageRequest(BaseModel):
    thread_id: str
    last_timestamp: int


class MessageDeleteRequest(BaseModel):
    thread_id: str


class SendChatMessageRequest(BaseModel):
    id: str
    thread_id: str
    text: str
    type: MessageType = MessageType.TEXT
    timestamp: int  # epoch milliseconds
    status: MessageStatus = MessageStatus.SENT


class LoginRequest(BaseModel):
    user_phone: str
    password: str
    timestamp: int


class LogOutRequest(BaseModel):
    user_id: str
    timestamp: int


class SignUpRequest(BaseModel):
    user_phone: str
    user_name: str
    password: str
    avatar_url: Optional[str] = ""
    fcm_token: Optional[str] = None
    user_platform: str
    timestamp: int


class SaveFcmTokenRequest(BaseModel):
    fcm_token: str
    user_platform: str


class UpdateUserRequest(BaseModel):
    user_status: str
    timestamp: int
