from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import redis.asyncio as redis
import asyncio

app = FastAPI()
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

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
                # Envia para todos conectados no chat
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

    # Se já houver gente no chat, redireciona
    if len(active_connections.get(room_id, [])) >= 1:
        await websocket.send_json({"redirect": f"/chat?room={room_id}"})
        waiting_connections[room_id].remove(websocket)
        await websocket.close()
        if not waiting_connections[room_id]:
            del waiting_connections[room_id]
        return

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        waiting_connections[room_id].remove(websocket)
        if not waiting_connections[room_id]:
            del waiting_connections[room_id]


@app.websocket("/ws/{room_id}/{client_name}")
async def chat_websocket(websocket: WebSocket, room_id: str, client_name: str):
    await websocket.accept()
    if room_id not in active_connections:
        active_connections[room_id] = []
    active_connections[room_id].append(websocket)

    # Cria task do redis se nao existir
    if room_id not in pubsub_tasks:
        pubsub_tasks[room_id] = asyncio.create_task(listen_to_redis(room_id))

    # Se tiver gente esperando, redireciona
    if room_id in waiting_connections:
        for wws in waiting_connections[room_id]:
            await wws.send_json({"redirect": f"/chat?room={room_id}"})
        del waiting_connections[room_id]

    try:
        while True:
            data = await websocket.receive_text()
            # Verifica se é o comando "/exit"
            if data.strip() == "/exit":
                # Encerra o chat para todos
                # 1) avisa os demais que o chat foi fechado
                for ws_conn in active_connections[room_id]:
                    if ws_conn is not websocket:
                        await ws_conn.send_text("chatClosed")
                        await ws_conn.close()
                # 2) encerra a si mesmo
                await websocket.close()
                # 3) remove todos dessa sala
                active_connections[room_id].clear()
                del active_connections[room_id]

                # Encerra a task do redis
                if room_id in pubsub_tasks:
                    pubsub_tasks[room_id].cancel()
                    del pubsub_tasks[room_id]

                break  # Sai do loop
            else:
                # Mensagem normal, publica no Redis
                await r.publish(room_id, f"{client_name}: {data}")

    except WebSocketDisconnect:
        # Se desconectou sem mandar "/exit"
        active_connections[room_id].remove(websocket)
        if not active_connections[room_id]:
            # Ninguém mais na sala, encerra
            del active_connections[room_id]
            if room_id in pubsub_tasks:
                pubsub_tasks[room_id].cancel()
                del pubsub_tasks[room_id]
