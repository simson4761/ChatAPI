import firebase_admin
from firebase_admin import credentials, messaging
import logging
import os
from dotenv import load_dotenv

load_dotenv()

key_path = os.getenv("FIREBASE_KEY_PATH")

creds = credentials.Certificate(key_path)
firebase_admin.initialize_app(credential=creds)

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def send_push_notification(fcm_token: str, message: str, sender_name: str, chat_id: str, thread_id: str):
    message = messaging.Message(
        token=fcm_token,
        notification=messaging.Notification(
            title=sender_name,
            body=message
        ),
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(channel_id=thread_id)
        ),
        data={
            "chat_id": chat_id,
            "thread_id": thread_id,
            "sender_name": sender_name
        }
    )

    logger.info("push notification sender name :" + sender_name)

    response = messaging.send(message=message)

    print(response)
