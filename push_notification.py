import firebase_admin
from firebase_admin import credentials, messaging

creds = credentials.Certificate("/Users/simson/PycharmProjects/chatAPI/privateKeys/service_account_key.json")
firebase_admin.initialize_app(credential=creds)


def send_push_notification(fcm_token: str, message: str, sender_name: str,chat_id: str, thread_id: str):
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

    response = messaging.send(message=message)

    print(response)
