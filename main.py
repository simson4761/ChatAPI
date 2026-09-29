from fastapi import HTTPException

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from firebase_admin.messaging import UnregisteredError
from sqlalchemy import text, func, update
from sqlalchemy.exc import IntegrityError, OperationalError
import logging

from sqlalchemy.orm import joinedload

import api_routers
import auth_service
import push_notification
from auth_service import get_current_user_id
from dataModels.conversationModels import Conversation, Participant
from dataModels.databaseModels.Base import Base
from dataModels.databaseModels.ChatMessageDB import ChatMessageDB
from dataModels.databaseModels.ConversationDB import ConversationDB
from dataModels.databaseModels.ConversationParticipantsDB import ConversationParticipantsDB
from dataModels.databaseModels.ParticipantDB import ParticipantDB
from dataModels.databaseModels.UserTokensDB import UserTokensDB
from dataModels.messageModels import ChatMessage
from dataModels.request_models import CreateConversationRequest, MessageDeleteRequest, SendChatMessageRequest, \
    LogOutRequest, SignUpRequest, SaveFcmTokenRequest, LoginRequest, UpdateUserRequest
from database import engine, session
from websocket_service import WebSocketManager

app = FastAPI()
web_socket_manager = WebSocketManager()

app.include_router(api_routers.auth_router)
app.include_router(api_routers.user_router)
app.include_router(api_routers.conversation_router)
app.include_router(api_routers.message_router)

logger = logging.getLogger(__name__)

# Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)


################################################################################################################
# Auth API calls
################################################################################################################
@api_routers.auth_router.post("/sign-up")
def sign_up_user(request: SignUpRequest):
    db = session()
    try:
        participant = db.query(ParticipantDB).filter(
            ParticipantDB.phone == request.user_phone
        ).first()

        if participant is not None:
            return {
                "success": False,
                "response_code": 200,
                "response_message": "Phone number already exists",
                "data": None,
                "error": None
            }

        user_id = auth_service.generate_user_id()

        access_token = auth_service.create_access_token(user_id)

        user_tokens = UserTokensDB(
            user_id=user_id,
            user_name=request.user_name,
            access_token=access_token,
            refresh_token=access_token,
            fcm_token=request.fcm_token,
            user_platform=request.user_platform,
            expires_at=int(request.timestamp) + 3600
        )

        user = ParticipantDB(
            user_id=user_id,
            name=request.user_name,
            phone=request.user_phone,
            password=auth_service.generateHash(request.password),
            avatar_url=request.avatar_url,
            last_seen=request.timestamp,
        )

        db.add(user_tokens)
        db.add(user)

        db.commit()

        db.refresh(user)

        return {
            "success": True,
            "response_code": 200,
            "response_message": "Signed up successfully",
            "data": {
                "user_id": user_id,
                "access_token": access_token,
                "refresh_token": access_token
            },
            "error": None
        }

    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        # db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error" + str(e))

    finally:
        db.close()


@api_routers.auth_router.post("/login")
def login(request: LoginRequest):
    db = session()
    try:
        participant = db.query(ParticipantDB).filter(
            ParticipantDB.phone == request.user_phone
        ).first()

        if participant is None:
            return {
                "success": False,
                "response_code": 200,
                "response_message": "Login Failed : User Not Found",
                "data": None,
                "error": None
            }
        else:

            access_token = auth_service.create_access_token(participant.user_id)

            password_matches = auth_service.verify_password(request.password, participant.password)

            if password_matches:

                result = db.execute(
                    update(UserTokensDB)
                    .where(UserTokensDB.user_id == participant.user_id)
                    .values(
                        access_token=access_token,
                        refresh_token=access_token,
                        expires_at=int(request.timestamp) + 3600,
                    )
                )

                if result.rowcount == 0:
                    return {
                        "success": False,
                        "response_code": 200,
                        "response_message": "Login Failed : User Not Found",
                        "data": None,
                        "error": None
                    }

                return {
                    "success": True,
                    "response_code": 200,
                    "response_message": "Request successful",
                    "data": {
                        "user_id": participant.user_id,
                        "access_token": access_token,
                        "refresh_token": access_token
                    },
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "response_code": 200,
                    "response_message": "Login Failed: Invalid Password",
                    "data": None,
                    "error": None
                }


    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        # db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error" + str(e))

    finally:
        db.close()


@api_routers.auth_router.post("/log-out")
def log_out(
        request: LogOutRequest
):
    db = session()
    try:
        participant = db.query(ParticipantDB).filter(
            ParticipantDB.user_id == request.user_id
        ).first()

        if participant is None:
            return {
                "success": False,
                "response_code": 200,
                "response_message": "Log-Out Failed : User Not Found",
                "data": None,
                "error": None
            }
        else:
            result = db.execute(
                update(UserTokensDB)
                .where(UserTokensDB.user_id == request.user_id)
                .values(
                    access_token=None,
                    refresh_token=None,
                    expires_at=None,
                )
            )

            if result.rowcount == 0:
                return {
                    "success": False,
                    "response_code": 200,
                    "response_message": "Log-Out Failed : User Not Found",
                    "data": None,
                    "error": None
                }

            return {
                "success": True,
                "response_code": 200,
                "response_message": "Log out successful",
                "data": None,
                "error": None
            }




    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        # db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error" + str(e))

    finally:
        db.close()


@api_routers.auth_router.post("/fcm-token")
def update_fcm_token(
        request: SaveFcmTokenRequest,
        user_id: str = Depends(get_current_user_id)
):
    db = session()

    try:
        result = db.execute(
            update(UserTokensDB)
            .where(UserTokensDB.user_id == user_id)
            .values(fcm_token=request.fcm_token)
        )
        db.commit()

        if result.rowcount == 0:
            return {
                "success": False,
                "response_code": 200,
                "response_message": "Fcm update Failed : User Not Found",
                "data": None,
                "error": None
            }
        else:
            return {
                "success": True,
                "response_code": 200,
                "response_message": "Fcm update done",
                "data": None,
                "error": None
            }


    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        # db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error" + str(e))

    finally:
        db.close()


################################################################################################################
# Websocket connection
################################################################################################################


@app.websocket("/websocket")
async def websocket(
        ws: WebSocket
):
    user_id = await auth_service.get_current_user_id_ws(ws)
    if user_id is None:
        return
    await web_socket_manager.connect(user_id=user_id, ws=ws)
    try:
        while True:
            data = await ws.receive_json()
            type_val = data.get("type")
            if type_val == "status_check":
                target_id = data.get("user_id")
                status = "online" if web_socket_manager.is_online(target_id=target_id) else "offline"
                await ws.send_json(
                    data={
                        "user_id": target_id,
                        "type": "broadcast",
                        "status": status
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        web_socket_manager.disconnect(user_id=user_id,ws=ws)


################################################################################################################
# Conversation API calls
################################################################################################################

@api_routers.conversation_router.get("/fetch")
def fetch_conversations(
        user_id: str = Depends(get_current_user_id),
):
    db = session()

    try:

        conversations = (
            db.query(ConversationDB)
            .join(ConversationParticipantsDB, ConversationParticipantsDB.thread_id == ConversationDB.thread_id)
            .filter(ConversationParticipantsDB.user_id == user_id)
            .options(joinedload(ConversationDB.participants).joinedload(ConversationParticipantsDB.participant))
            .all()
        )

        if not conversations:
            return {
                "success": False,
                "response_code": 200,
                "response_message": "No conversation Found",
                "data": [],
                "error": None
            }

        conversation_list = [
            Conversation(
                thread_id=row.thread_id,
                display_name=row.display_name,
                last_message_id=row.last_message_id,
                unread_count=row.unread_count,
            )
            for row in conversations
        ]

        return {
            "success": True,
            "response_code": 200,
            "response_message": "Request successful",
            "data": conversation_list,
            "error": None
        }


    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        # db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error" + str(e))

    finally:
        db.close()


@api_routers.conversation_router.get("/threads")
def fetch_all_threads(
        user_id: str = Depends(get_current_user_id),
):
    db = session()
    try:
        user_thread_ids = db.query(ConversationParticipantsDB.thread_id).filter(
            ConversationParticipantsDB.user_id == user_id
        ).subquery()

        # Step 2: all participant rows for those threads
        participants = db.query(
            ConversationParticipantsDB.user_id,
            ConversationParticipantsDB.thread_id
        ).filter(
            ConversationParticipantsDB.thread_id.in_(
                db.query(user_thread_ids.c.thread_id)
            ),
            ConversationParticipantsDB.user_id != user_id
        ).all()

        return {
            "success": True,
            "response_code": 200,
            "response_message": "Request successful",
            "data": [
                {"user_id": p.user_id, "thread_id": p.thread_id}
                for p in participants
            ],
            "error": None
        }

    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        # db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error" + str(e))

    finally:
        db.close()


@api_routers.conversation_router.post("/create")
def create_new_conversation(
        request: CreateConversationRequest,
        user_id: str = Depends(get_current_user_id),
):
    db = session()

    try:

        db_conversation = ConversationDB(
            thread_id=request.conversation.thread_id,
            display_name=request.conversation.display_name,
            last_message_id=request.conversation.last_message_id,
            unread_count=request.conversation.unread_count,
        )

        conversation_participant_1 = ConversationParticipantsDB(
            thread_id=request.conversation.thread_id,
            user_id=user_id
        )

        conversation_participant_2 = ConversationParticipantsDB(
            thread_id=request.conversation.thread_id,
            user_id=request.participant_id
        )

        db.add(conversation_participant_1)

        db.add(conversation_participant_2)

        db.add(db_conversation)

        db.commit()

        db.refresh(db_conversation)

        return {
            "success": True,
            "response_code": 200,
            "response_message": "Request successful",
            "data": None,
            "error": None
        }

    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()


@api_routers.conversation_router.post("/check")
def check_for_existing_convo(
        participant: Participant,
        user_id: str = Depends(get_current_user_id)
):
    db = session()
    try:
        user_threads = db.query(ConversationParticipantsDB.thread_id).filter(
            ConversationParticipantsDB.user_id == user_id
        ).scalar_subquery()

        common_threads = db.query(ConversationParticipantsDB.thread_id).filter(
            ConversationParticipantsDB.user_id == participant.user_id,
            ConversationParticipantsDB.thread_id.in_(user_threads)
        ).scalar_subquery()

        thread_id = db.query(ConversationParticipantsDB.thread_id).filter(
            ConversationParticipantsDB.thread_id.in_(common_threads)
        ).group_by(ConversationParticipantsDB.thread_id).having(
            func.count(ConversationParticipantsDB.user_id) == 2
        ).scalar()

        if thread_id is None:
            return {
                "success": False,
                "response_code": 200,
                "response_message": "Conversation not present",
                "data": None,
                "error": None
            }
        else:
            return {
                "success": True,
                "response_code": 200,
                "response_message": "Conversation present",
                "data": thread_id,
                "error": None
            }


    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()


@api_routers.conversation_router.post("/delete")
def delete_conversation(
        request: MessageDeleteRequest,
        user_id: str = Depends(get_current_user_id)
):
    db = session()
    try:
        query_msg = text("DELETE FROM conversations WHERE thread_id = :thread_id and user_id = :user_id")

        db.execute(
            query_msg,
            {
                "thread_id": request.thread_id,
                "user_id": user_id
            }
        )

        db.commit()

        return {
            "success": True,
            "response_code": 200,
            "response_message": "Request successful",
            "data": None,
            "error": None
        }


    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()


################################################################################################################
# Message API calls
################################################################################################################


@api_routers.message_router.get("/fetch/{thread_id}")
def fetchAllMessages(
        thread_id: str,
        user_id: str = Depends(get_current_user_id)
):
    db = session()
    try:

        messages = (
            db.query(ChatMessageDB)
            .filter(ChatMessageDB.thread_id == thread_id)
            .order_by(ChatMessageDB.timestamp.asc())
            .all()
        )

        return {
            "success": True,
            "response_code": 200,
            "response_message": "Request successful",
            "data": [
                ChatMessage(
                    id=m.chat_id,
                    thread_id=m.thread_id,
                    user_id=m.user_id,
                    text=m.text,
                    type=m.type,
                    timestamp=m.timestamp,
                    status=m.status
                )
                for m in messages
            ],
            "error": None
        }

    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()


@api_routers.message_router.get("/new")
def new_messages(
        thread_id: str,
        after_timestamp: str,
        user_id: str = Depends(get_current_user_id)
):
    db = session()
    try:

        messages = (
            db.query(ChatMessageDB)
            .filter(ChatMessageDB.thread_id == thread_id)
            .filter(ChatMessageDB.timestamp > int(after_timestamp))
            .order_by(ChatMessageDB.timestamp.asc())
            .all()
        )

        participants = (
            db.query(ParticipantDB)
            .join(
                ConversationParticipantsDB,
                ConversationParticipantsDB.user_id == ParticipantDB.user_id,
            )
            .filter(ConversationParticipantsDB.thread_id == thread_id)
            .all()
        )

        messages = [
            ChatMessage(
                id=m.chat_id,
                thread_id=m.thread_id,
                user_id=m.user_id,
                text=m.text,
                type=m.type,
                timestamp=m.timestamp,
                status=m.status
            )
            for m in messages
        ]

        return {
            "success": True,
            "response_code": 200,
            "response_message": "Request successful",
            "data": {
                "participants": participants,
                "messages": messages
            },
            "error": None
        }

    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()


@api_routers.message_router.post("/send")
def send_message(
        message: SendChatMessageRequest,
        user_id: str = Depends(get_current_user_id)
):
    db = session()

    try:

        msg_db = ChatMessageDB(
            user_id=user_id,
            chat_id=message.id,
            thread_id=message.thread_id,
            text=message.text,
            type=str(message.type.name),
            timestamp=message.timestamp,
            status=str(message.status.name),
        )

        db.add(msg_db)

        db.commit()

        db.refresh(msg_db)

        conversation_participants = (
            db.query(ConversationParticipantsDB)
            .filter(ConversationParticipantsDB.thread_id == message.thread_id)
            .filter(ConversationParticipantsDB.user_id != user_id)
            .all()
        )

        user_tokens = []

        for participant in conversation_participants:
            user_token = (
                db.query(UserTokensDB)
                .filter(UserTokensDB.user_id == participant.user_id)
                .first()
            )

            user_tokens.append(user_token)

        if len(user_tokens) > 0:
            for user in user_tokens:
                try:
                    push_notification.send_push_notification(
                        chat_id=message.id,
                        thread_id=message.thread_id,
                        fcm_token=user.fcm_token,
                        message=message.text,
                        sender_name=user.user_name
                    )

                except UnregisteredError:
                    # remove_token_from_db(token)
                    logger.warning(f"Unregistered FCM user")
                except Exception as e:
                    logger.warning(f"Push notification failed: {e}")

        else:
            logger.warning("Fcm token not found for user")

        return {
            "success": True,
            "response_code": 200,
            "response_message": "Request successful",
            "data": None,
            "error": None
        }
    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()


@api_routers.message_router.post("/update")
def update_message(
        updated_message: ChatMessage
):
    db = session()

    try:
        query = text("""UPDATE messages SET text = %s,
             type = %s
            timestamp = %s
            status = %s
            WHERE chat_id = %s""")
        result = db.execute(
            query,
            (updated_message.text, updated_message.type, updated_message.timestamp, updated_message.status)
        )

        if result.rowCount == 0:
            db.rollback()
            raise HTTPException(404, "Not found")

        db.commit()
    except HTTPException:
        raise  # let FastAPI handle expected errors as-is

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error updating message: {e}")
        raise HTTPException(409, "Conflict updating message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error updating message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()

    return {
        "success": True,
        "response_code": 200,
        "response_message": "Message updated successfully",
        "data": None,
        "error": None
    }


@api_routers.message_router.post("/delete")
def delete_message(
        req: MessageDeleteRequest,
        user_id: str = Depends(get_current_user_id)
):
    db = session()

    try:

        db.execute(
            "DELETE FROM messages WHERE chat_id = %s AND thread_id = %s",
            (req.chat_id, req.thread_id)
        )
        db.commit()
        return {
            "success": True,
            "response_code": 200,
            "response_message": "Message deleted successfully",
            "data": None,
            "error": None
        }

    except HTTPException:
        raise

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error deleting message: {e}")
        raise HTTPException(409, "Conflict deleting message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error deleting message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()


################################################################################################################
# Account API calls
################################################################################################################

@api_routers.user_router.get("/fetch/{key}")
def get_users(
        key: str = "",
        user_id: str = Depends(get_current_user_id)
):
    db = session()

    try:
        users = (
            db.query(ParticipantDB)
            .filter(ParticipantDB.phone == key)
            .filter(ParticipantDB.user_id != user_id)
            .limit(20)
            .all()
        )
        return {
            "success": True,
            "response_code": 200,
            "response_message": "Request successful",
            "data": users,
            "error": None
        }

    except HTTPException:
        raise  # let FastAPI handle expected errors as-is

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error updating message: {e}")
        raise HTTPException(409, "Conflict updating message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error updating message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()


@api_routers.user_router.get("/fetch")
def get_all_users(
        user_id: str = Depends(get_current_user_id)
):
    db = session()

    try:
        users = (
            db.query(ParticipantDB)
            .filter(ParticipantDB.user_id != user_id)
            .all()
        )
        return {
            "success": True,
            "response_code": 200,
            "response_message": "Request successful",
            "data": users,
            "error": None
        }

    except HTTPException:
        raise  # let FastAPI handle expected errors as-is

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error updating message: {e}")
        raise HTTPException(409, "Conflict updating message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error updating message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()


@api_routers.user_router.post("/update")
def update_user_status(
        request: UpdateUserRequest,
        user_id: str = Depends(get_current_user_id)
):
    db = session()
    try:
        user = db.query(ParticipantDB).filter(ParticipantDB.user_id == user_id)

        if user is None:
            return {
                "success": False,
                "response_code": 200,
                "response_message": "User not found",
                "data": None,
                "error": None
            }

        result = db.execute(
            update(ParticipantDB)
            .where(ParticipantDB.user_id == user_id)
            .values(

            )
        )

        db.commit()

        db.refresh(user)

        return {
            "success": True,
            "response_code": 200,
            "response_message": "User updated successfully",
            "data": Participant.model_validate(user).model_dump(),
            "error": None
        }



    except HTTPException:
        raise  # let FastAPI handle expected errors as-is

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error updating message: {e}")
        raise HTTPException(409, "Conflict updating message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error updating message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()


@api_routers.user_router.post("/update")
def update_user(
        user_profile: Participant,
        user_id: str = Depends(get_current_user_id)
):
    db = session()
    try:
        user = db.query(ParticipantDB).filter(ParticipantDB.user_id == user_id)

        if user is None:
            return {
                "success": False,
                "response_code": 200,
                "response_message": "User not found",
                "data": None,
                "error": None
            }

        updated_user = user_profile.model_dump(exclude_unset=True)

        updated_user.pop("user_id", None)

        for field, value in updated_user.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "response_code": 200,
            "response_message": "User updated successfully",
            "data": Participant.model_validate(user).model_dump(),
            "error": None
        }



    except HTTPException:
        raise  # let FastAPI handle expected errors as-is

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error updating message: {e}")
        raise HTTPException(409, "Conflict updating message")

    except OperationalError as e:
        db.rollback()
        logger.error(f"DB connection/operational error: {e}")
        raise HTTPException(503, "Database unavailable, try again later")

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error updating message: {e}")
        raise HTTPException(500, "Internal server error")

    finally:
        db.close()
