from jinja2 import Template, FileSystemLoader, Environment
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import HTMLResponse
import uvicorn
import time
from typing import List, Dict, Optional
from threading import Lock

from functools import wraps

import spchat.db.sessionlocal as db
import spchat.db.ops as dbops
from spchat.db import queries
from spchat.db.models import MessageIn, Message


def locking(method):

    @wraps(method)
    def inner(ref, *args, **kwargs):
        ref.lock.acquire()
        ret = method(ref, *args, **kwargs)
        ref.lock.release()
        return ret

    return inner


# Initialize and decorate FastAPI app
app = FastAPI()

db.init_db()
db.decorate_app(app)

PORT = 4242
HOST = "0.0.0.0"

# Setup html templating engine
loader = FileSystemLoader("spchat/templates")
template_env = Environment(loader=loader)

welcome_temp = template_env.get_template("welcome.html")
chat_area_temp = template_env.get_template("chat-area.html")
message_temp = template_env.get_template("message.html")
self_message_temp = template_env.get_template("self_message.html")
serv_message_temp = template_env.get_template("server_message.html")


# Define connection manager class
class ConnMan:
    """Manages a set of key-value pairs client_id->websocket.
    """

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


# instantiate the connection manager
manager = ConnMan()


# Defiene path operations
@app.get("/")
async def get_home():
    return HTMLResponse(welcome_temp.render(host=HOST, port=PORT))


@app.get("/all_messages", response_model=List[Message])
async def all_messages():
    q = db.tables.messages.select()
    return await db.database.fetch_all(q)


@app.post("/room")
async def get_room(handle: str = Form(...),
                   #req=Depends(log_request_info),
                   ):
    return HTMLResponse(chat_area_temp.render(client_id=handle))


# Define the message rendering function
format_data = "%d/%m/%y %H:%M:%S"


def mk_message_el(chat_message,
                  from_id: Optional[str],
                  temp=message_temp,
                  dt: datetime = None):
    """Render the htmx for a message given string content `chat_message`,
    client_id of the sender (optional, pass None for self_message),
    a datetime (optional, do not pass to have now() as dt).
    By default uses the `message_temp` template. Pass the appropriate template
    if desired message is a self or server message
    """
    if dt is None:
        dt = datetime.now()
    tm = dt.strftime(format_data)
    return temp.render(time=tm, message=chat_message, client_id=from_id)


# Define sync procedure
async def sync_old_messages(ws: WebSocket, client_id: str):
    """Syncronize old messages with the given client websocket.
    client_id is used to determine which of the messages in the history
    are from the user associated with the current websocket
    """
    print("sync...")

    async def proc_fn(row):
        #print(row)
        temp = message_temp
        from_id = row["user_from"]
        if from_id == client_id:
            temp = self_message_temp
            from_id = None
        msg = mk_message_el(row["chat_message"],
                            from_id=from_id,
                            temp=temp,
                            dt=row["at"])
        await ws.send_text(msg)

    await queries.forall_in_q(db.database, queries.all_messages_q(), proc_fn)


# WebSocket endpoint


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    # establish conn
    await manager.connect(client_id, websocket)
    # sync old messages
    await sync_old_messages(websocket, client_id)
    # message loop
    try:
        while True:
            data = await websocket.receive_json()
            # save message to db
            msg_in = MessageIn(user_from=client_id,
                               chat_message=data["chat_message"],
                               at=datetime.now())

            insert_op = dbops.insert_msg_op(msg_in)
            msg_id = await db.database.execute(insert_op)

            # send message to sender as self message
            pm = mk_message_el(data["chat_message"],
                               from_id=None,
                               temp=self_message_temp)
            await manager.send_pm(client_id, pm)

            # send message to the others as standard (signed) message
            bm = mk_message_el(data["chat_message"], from_id=client_id)
            await manager.broadcast_from(client_id, bm)

    # Handle disconnection
    except WebSocketDisconnect:
        msg = f"Client @{client_id} left the room"
        print(msg)
        manager.disconnect(client_id)
        await manager.broadcast(
            mk_message_el(msg, from_id="server", temp=serv_message_temp))


if __name__ == "__main__":

    uvicorn.run("spchat.room1:app",
                host=HOST,
                port=PORT,
                reload=True,
                reload_includes=["*.py", "*.html"])
