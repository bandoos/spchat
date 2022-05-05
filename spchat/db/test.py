from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, DateTime, MetaData
import sqlalchemy as sql
from dataclasses import dataclass

SQLITE = 'sqlite'
MESSAGES = 'messages'


@dataclass
class AppTables:
    messages: Table


class MyDriver:
    DB_ENGINE = {SQLITE: 'sqlite:///{DB}'}

    db_engine = None

    def __init__(self, dbtype, username="", password="", dbname=""):
        dbtype = dbtype.lower()
        if dbtype in self.DB_ENGINE.keys():
            engine_url = self.DB_ENGINE[dbtype].format(DB=dbname)
            self.db_engine = create_engine(engine_url)
            print(self.db_engine)
        else:
            raise Exception(f"DBTYPE {dbtype} not found")

    def create_tables(self):
        meta = MetaData()

        messages = Table(
            MESSAGES,
            meta,
            Column('id', Integer, primary_key=True),
            Column('user_from', String, nullable=False),
            Column('chat_message', String, nullable=False),
            Column('at', DateTime, nullable=False),
        )

        self.tables = AppTables(messages=messages)

        try:
            meta.create_all(self.db_engine)
            print("Tables created successfully")
        except Exception as e:
            print("Error during table creation")
            print(e)


from datetime import datetime


def dummy_populate(dbms: MyDriver, n: int):
    with dbms.db_engine.connect() as conn:
        result = conn.execute(sql.insert(dbms.tables.messages),
                              [{
                                  "user_from": "sandy",
                                  "chat_message": f"Sandy says {i}",
                                  "at": datetime.now()
                              } for i in range(n)])
        #conn.commit()


def all_messages(dbms: MyDriver):

    q = sql.select([dbms.tables.messages])
    conn = dbms.db_engine.connect()
    rp = conn.execute(q)
    return rp.fetchall()


from pprint import pprint


def example_0():
    dbms = MyDriver(SQLITE, dbname="mydb.sqlite")

    dbms.create_tables()

    dummy_populate(dbms, 10)

    pprint(all_messages(dbms))
