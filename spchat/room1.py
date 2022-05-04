from jinja2 import Template, FileSystemLoader, Environment
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import HTMLResponse
import uvicorn
import time
from typing import List, Dict
from threading import Lock

from functools import wraps


def locking(method):

    @wraps(method)
    def inner(ref, *args, **kwargs):
        ref.lock.acquire()
        ret = method(ref, *args, **kwargs)
        ref.lock.release()
        return ret

    return inner


app = FastAPI()

PORT = 4242
HOST = "0.0.0.0"

loader = FileSystemLoader("spchat/templates")
template_env = Environment(loader=loader)

welcome_temp = template_env.get_template("welcome.html")
chat_area_temp = template_env.get_template("chat-area.html")
message_temp = template_env.get_template("message.html")
self_message_temp = template_env.get_template("self_message.html")
serv_message_temp = template_env.get_template("server_message.html")


class ConnMan:
    # TODO: ensure thread safety!

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.lock = Lock()

    @locking
    async def connect(self, client_id: str, ws: WebSocket):
        await ws.accept()
        self.active_connections[client_id] = ws

    @locking
    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    @locking
    async def send_pm(self, client_id: str, msg: str):
        ws = self.active_connections.get(client_id)
        if not (ws is None):
            await ws.send_text(msg)

    @locking
    async def broadcast(self, msg: str):
        for conn in self.active_connections.values():
            await conn.send_text(msg)

    @locking
    async def broadcast_from(self, client_id: str, msg: str):
        for key, conn in self.active_connections.items():
            if key != client_id:
                await conn.send_text(msg)


manager = ConnMan()


@app.get("/")
async def get_home():
    return HTMLResponse(welcome_temp.render(host=HOST, port=PORT))


@app.post("/room")
async def get_room(handle: str = Form(...),
                   #req=Depends(log_request_info),
                   ):
    return HTMLResponse(chat_area_temp.render(client_id=handle))


format_data = "%d/%m/%y %H:%M:%S"


def mk_message_el(chat_message, temp=message_temp):
    tm = datetime.now().strftime(format_data)
    return temp.render(time=tm, message=chat_message)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            #print(data["chat_message"])
            pm = mk_message_el(data["chat_message"], temp=self_message_temp)
            await manager.send_pm(client_id, pm)
            bm = mk_message_el(
                f"<span class='font-size-12'>@{client_id}</span><br/>" +
                data["chat_message"])
            await manager.broadcast_from(client_id, bm)
    except WebSocketDisconnect:
        msg = f"Client @{client_id} left the room"
        print(msg)
        manager.disconnect(client_id)
        await manager.broadcast(mk_message_el(msg, temp=serv_message_temp))


if __name__ == "__main__":

    uvicorn.run("spchat.room1:app",
                host=HOST,
                port=PORT,
                reload=True,
                reload_includes=["*.py", "*.html"])
