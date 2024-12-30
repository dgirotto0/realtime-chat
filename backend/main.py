# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import asyncio
import os

app = FastAPI()

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

active_connections = {}
waiting_connections = {}
pubsub_tasks = {}

async def listen_to_redis(room_id: str):
    pubsub = r.pubsub()
    await pubsub.subscribe(room_id)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                for ws in active_connections.get(room_id, []):
                    await ws.send_text(data)
    except asyncio.CancelledError:
        await pubsub.unsubscribe(room_id)
        raise

@app.websocket("/ws/waiting/{room_id}")
async def waiting_websocket(websocket: WebSocket, room_id: str):
    await websocket.accept()
    if room_id not in waiting_connections:
        waiting_connections[room_id] = []

    waiting_connections[room_id].append(websocket)
    print(f"[WaitingRoom] Cliente aguardando na sala {room_id}")

    # Loop para manter conexão ativa
    try:
        while True:
            data = await websocket.receive_text()
            if len(active_connections.get(room_id, [])) > 0:
                await websocket.send_json({"redirect": f"/chat?room={room_id}"})
                await websocket.close()
                break
    except WebSocketDisconnect:
        print(f"[WaitingRoom] Cliente desconectado da sala {room_id}")
        if websocket in waiting_connections[room_id]:
            waiting_connections[room_id].remove(websocket)

@app.websocket("/ws/{room_id}/{client_name}")
async def chat_websocket(websocket: WebSocket, room_id: str, client_name: str):
    await websocket.accept()
    print(f"[Chat] {client_name} conectado na sala {room_id}")

    if room_id not in active_connections:
        active_connections[room_id] = []
    active_connections[room_id].append(websocket)

    if room_id not in pubsub_tasks:
        pubsub_tasks[room_id] = asyncio.create_task(listen_to_redis(room_id))

    # Notificar quem está aguardando
    if room_id in waiting_connections:
        for wws in waiting_connections[room_id]:
            try:
                print(f"Redirecionando cliente para sala {room_id}")
                await wws.send_json({"redirect": f"/chat?room={room_id}"})
            except WebSocketDisconnect:
                # Se estava desconectado, ignoramos
                pass
        del waiting_connections[room_id]

    try:
        while True:
            data = await websocket.receive_text()
            if data == "/exit":
                break
            await r.publish(room_id, f"{client_name}: {data}")
    except WebSocketDisconnect:
        print(f"[Chat] {client_name} desconectou da sala {room_id}")
    finally:
        active_connections[room_id].remove(websocket)
