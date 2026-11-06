from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.active_users: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        old_connection = self.active_users.get(user_id)

        if old_connection is not None:
            try:
                await old_connection.close(code=4000)
            except Exception:
                pass
        self.active_users[user_id] = ws
        print("connected")

    def disconnect(self, user_id: str, ws: WebSocket):
        if self.active_users.get(user_id) is ws:
            del self.active_users[user_id]

    def is_online(self, target_id: str) -> bool:
        return self.active_users.__contains__(target_id)

    def send_to(self,target_id: str, data : str) -> bool:
        ws = self.active_users[target_id]
        if ws is None:
            return False

        try:
            ws.send_json(data)
            return True
        except Exception:
            self.disconnect(target_id, ws)
            return False

