import uuid
from datetime import timedelta, datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from starlette import status
from starlette.websockets import WebSocket

SECRET_KEY = "load-from-env"  # os.environ["SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(minutes=60)

password_hasher = PasswordHasher()
bearer = HTTPBearer()


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def generate_user_id() -> str:
    return str(uuid.uuid4())


def generateHash(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def get_current_user_id(
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> str:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:  # covers bad signature and expired tokens
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    return user_id


async def get_current_user_id_ws(websocket: WebSocket) -> str | None:
    """
    Same validation as get_current_user_id, but reads the token from
    a WebSocket instead of an HTTP Request, since HTTPBearer/Depends
    doesn't work on websocket routes.
    Returns None (and closes the socket) if auth fails.
    """
    auth_header = websocket.headers.get("Authorization")
    token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    if token is None:
        token = websocket.query_params.get("token")  # fallback

    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    user_id = payload.get("sub")
    if not user_id or payload.get("type") != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    return user_id
