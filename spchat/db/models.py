from pydantic import BaseModel
from datetime import datetime


class MessageIn(BaseModel):
    user_from: str
    chat_message: str
    at: datetime


class Message(MessageIn):
    id: int
