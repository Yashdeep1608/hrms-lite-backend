import socketio
from app.core.security import decode_access_token

sio = socketio.AsyncServer(
    cors_allowed_origins="*",  # Dev only
    async_mode='asgi',
)
socket_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ, auth):
    print("CONNECT", auth)
    token = auth.get("token")
    if not token:
        raise ConnectionRefusedError("Missing token")

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise ConnectionRefusedError("Invalid user")

        await sio.save_session(sid, {"user_id": user_id})
        await sio.enter_room(sid, f"user_{user_id}")
        print(f"User {user_id} connected to room user_{user_id}")
    except Exception as e:
        print("Auth error:", e)
        raise ConnectionRefusedError("Invalid token")

@sio.event
async def disconnect(sid):
    print("DISCONNECTED", sid)
