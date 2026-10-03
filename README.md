# chatAPI

A self-hosted, one-to-one, one-to-many chat backend built with **FastAPI** and **PostgreSQL**. It provides phone-number based accounts, JWT authentication, conversation and message storage, Firebase Cloud Messaging (FCM) push notifications, and a WebSocket endpoint for online/offline presence.

## Features

- Sign up / login / logout with Argon2 password hashing
- JWT (HS256) access tokens, validated on both HTTP and WebSocket routes
- One-to-one and one-to-many conversations and group chat (create, check for existing, list, delete)
- Message send, fetch, incremental sync (`after_timestamp`), update, delete
- Push notifications to the recipient via Firebase Admin SDK
- WebSocket presence: connect, `status_check` for any user, single active connection per user
- Account lookup by phone number

## Tech Stack

| Layer | Tech |
|---|---|
| Framework | FastAPI |
| ORM / DB | SQLAlchemy 2.x, PostgreSQL (`psycopg` v3 driver) |
| Auth | `python-jose` (JWT), `argon2-cffi` |
| Push | `firebase-admin` (FCM) |
| Validation | Pydantic |

## Project Structure

```
chatapi/
├── main.py                  # App entry point + all route handlers
├── api_routers.py           # APIRouter definitions (auth, account, conversations, chat)
├── auth_service.py          # JWT creation/validation, password hashing, WS auth
├── database.py              # SQLAlchemy engine + session factory
├── database_service.py      # (placeholder)
├── push_notification.py     # FCM push helper
├── websocket_service.py     # WebSocketManager (active connections, presence)
└── dataModels/
    ├── conversationModels.py    # Participant, Conversation, ApiResponse
    ├── messageModels.py         # ChatMessage, MessageType, MessageStatus
    ├── request_models.py        # Request bodies
    └── databaseModels/          # SQLAlchemy models
        ├── Base.py
        ├── ParticipantDB.py
        ├── UserTokensDB.py
        ├── ConversationDB.py
        ├── ConversationParticipantsDB.py
        └── ChatMessageDB.py
```

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL
- A Firebase project with a service account key (for push notifications)

### Install

```bash
git clone https://github.com/simson4761/chatapi.git
cd chatapi
python -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" sqlalchemy "psycopg[binary]" \
            python-jose argon2-cffi firebase-admin pydantic
```

### Configure

Create the database:

```sql
CREATE DATABASE "chatDatabase";
```

Then set these values (move them out of source and into environment variables or a `.env` file):

| Setting | Where it lives now | Description |
|---|---|---|
| `SECRET_KEY` | `auth_service.py` | JWT signing secret. Use a long random value, e.g. `openssl rand -hex 32` |
| `DATABASE_URL` | `database.py` | e.g. `postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/chatDatabase` |
| `FIREBASE_CREDENTIALS` | `push_notification.py` | Path to the Firebase service account JSON |

> Never commit secrets or the service account key. Keep them in the environment and add `privateKeys/` and `.env` to `.gitignore`.

### Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Tables are created automatically on startup via `Base.metadata.create_all(engine)`.

Interactive docs: `http://localhost:8000/docs`

## Authentication

Protected routes expect a bearer token:

```
Authorization: Bearer <access_token>
```

The WebSocket accepts the same header, or a `?token=<access_token>` query parameter as a fallback. Access tokens expire after 60 minutes.

## API Overview

All responses use a common envelope:

```json
{
  "success": true,
  "response_code": 200,
  "response_message": "Request successful",
  "data": null,
  "error": null
}
```

### Auth (`/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/sign-up` | No | Create an account, returns tokens |
| POST | `/auth/login` | No | Login with phone + password |
| POST | `/auth/log-out` | No | Clear stored tokens for a user |
| POST | `/auth/fcm-token` | Yes | Update the device FCM token |

### Account (`/account`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/account/fetch` | Yes | List all other users |
| GET | `/account/fetch/{key}` | Yes | Find users by phone number |
| POST | `/account/update` | Yes | Update profile (work in progress) |

### Conversations (`/conversations`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/conversations/fetch` | Yes | Conversations the user belongs to |
| GET | `/conversations/threads` | Yes | Other participants per thread |
| POST | `/conversations/create` | Yes | Create a 1:1 conversation |
| POST | `/conversations/check` | Yes | Check if a 1:1 thread already exists with a user |
| POST | `/conversations/delete` | Yes | Delete a conversation |

### Messages (`/chat`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/chat/fetch/{thread_id}` | Yes | All messages in a thread, oldest first |
| GET | `/chat/new?thread_id=&after_timestamp=` | Yes | Messages newer than a timestamp, plus participants |
| POST | `/chat/send` | Yes | Store a message and push-notify the recipient |
| POST | `/chat/update` | Yes | Update a message |
| POST | `/chat/delete` | Yes | Delete a message |

### WebSocket

`ws://host:8000/websocket`

Client to server:

```json
{ "type": "status_check", "user_id": "<target user id>" }
```

Server to client:

```json
{ "user_id": "<target user id>", "type": "broadcast", "status": "online" }
```

Opening a new connection for the same user closes the previous one with code `4000`.

## Data Model

- **participants**: `user_id`, `name`, `phone`, `password` (Argon2 hash), `avatar_url`, `last_seen`
- **user_tokens**: `user_id`, `user_name`, `access_token`, `refresh_token`, `user_platform`, `fcm_token`, `expires_at`
- **conversations**: `thread_id`, `display_name`, `last_message_id`, `unread_count`
- **conversation_participants**: `(thread_id, user_id)` composite key
- **messages**: `chat_id`, `user_id`, `thread_id`, `text`, `type`, `timestamp` (epoch ms), `status`

Message types: `TEXT`, `IMAGE`, `VIDEO`, `AUDIO`, `FILE`, `LOCATION`, `SYSTEM`
Message statuses: `QUEUED`, `SENT`, `RECEIVED`, `SEEN`, `FAILED`

## Known Issues / TODO

- Load `SECRET_KEY`, DB URL and Firebase credentials from environment variables
- `login` updates tokens but never calls `db.commit()`
- `/chat/delete` and `/chat/update` use raw `%s` SQL with `db.execute`; switch to SQLAlchemy `text()` with named parameters (the update query is also missing a comma and the `chat_id` parameter)
- `/conversations/delete` queries `conversations` by `user_id`, a column that table does not have
- Two handlers are registered on `POST /account/update`; the second one never runs, and both need the query `.first()` and a real update body
- `/chat/send` sends the notification title and token lookup against the recipient; the title should be the sender's name
- `/chat/fetch` and `/chat/new` don't verify the caller belongs to the thread
- `/auth/log-out` should require authentication
- `WebSocketManager.send_to` doesn't `await` `send_json` and raises `KeyError` for offline users
- Refresh tokens currently equal access tokens; add a real refresh flow
- Copy-pasted error messages ("deleting message") in many handlers should be made specific
- `database_service.py` is empty; move the query logic out of `main.py` and split routes per router module
- Add Alembic migrations in place of `create_all`, plus tests

## License

Add a license of your choice.
