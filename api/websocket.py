from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from api.auth import JWT_ALGORITHM, JWT_SECRET_KEY
from orchestration.queue import get_redis

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def session_events(websocket: WebSocket, session_id: UUID, token: str = Query(...)) -> None:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if not payload.get("sub"):
            raise ValueError("missing sub")
    except (JWTError, ValueError):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    redis_client = await get_redis()
    pubsub = redis_client.pubsub()
    channel = f"agentforge:events:{session_id}"
    await pubsub.subscribe(channel)

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("data"):
                data = message["data"]
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode("utf-8")
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    parsed = {"event": "raw", "payload": data}
                await websocket.send_json(parsed)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


async def publish_session_event(session_id: UUID, event: dict) -> None:
    redis_client = await get_redis()
    await redis_client.publish(f"agentforge:events:{session_id}", json.dumps(event, default=str))
