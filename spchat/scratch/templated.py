from jinja2 import Template, FileSystemLoader, Environment
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

PORT = 4242
HOST = "0.0.0.0"

loader = FileSystemLoader("spchat/templates")
template_env = Environment(loader=loader)

templ_name = "01-chat.html"
temp = template_env.get_template(templ_name)


@app.get("/")
async def get():
    return HTMLResponse(temp.render(host=HOST, port=PORT))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"=> {data}")


if __name__ == "__main__":
    uvicorn.run("spchat.scratch.templated:app",
                host=HOST,
                port=PORT,
                reload=True)
