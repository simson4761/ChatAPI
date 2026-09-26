from fastapi import APIRouter

conversation_router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)

message_router = APIRouter(
    prefix="/chat",
    tags=["Messages"]
)

auth_router = APIRouter(
    prefix="/auth",
    tags=["Authorization"]
)

user_router = APIRouter(
    prefix="/account",
    tags=["Account"]
)

