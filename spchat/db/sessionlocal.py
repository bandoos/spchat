from typing import List
import databases
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, DateTime, MetaData
import sqlalchemy as sql
from dataclasses import dataclass


@dataclass
class AppTables:
    messages: Table


DATABASE_URL = "sqlite:///./mydb.sqlite"

database = databases.Database(DATABASE_URL)

meta = sql.MetaData()

MESSAGES = 'messages'

tables = AppTables(messages=Table(
    MESSAGES,
    meta,
    Column('id', Integer, primary_key=True),
    Column('user_from', String, nullable=False),
    Column('chat_message', String, nullable=False),
    Column('at', DateTime, nullable=False),
))

engine = sql.create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def init_db():
    meta.create_all(engine)


def decorate_app(app):

    @app.on_event("startup")
    async def startup():
        await database.connect()

    @app.on_event("shutdown")
    async def shutdown():
        await database.disconnect()
