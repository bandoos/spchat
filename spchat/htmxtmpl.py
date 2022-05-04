from jinja2 import Template, FileSystemLoader, Environment
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn
import time

app = FastAPI()

PORT = 4242
HOST = "0.0.0.0"

loader = FileSystemLoader("spchat/templates")
template_env = Environment(loader=loader)

templ_name = "02-htmx-chat.html"
temp = template_env.get_template(templ_name)


@app.get("/")
async def get():
    return HTMLResponse(temp.render(host=HOST, port=PORT))


def mk_message_el(chat_message):
    tm = time.time()
    cont = """
    <div hx-swap-oob="beforeend:#content">
        <p>{time}: {message}</p>
    </div>

    """
    return cont.format(time=tm, message=chat_message)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        print(data["chat_message"])
        await websocket.send_text(mk_message_el(data["chat_message"]))


if __name__ == "__main__":
    uvicorn.run("spchat.htmxtmpl:app", host=HOST, port=PORT, reload=True)
