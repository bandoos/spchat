from spchat.db.sessionlocal import tables
from pprint import pprint
import asyncio
from databases import Database


# Utils
def test_coroutine(asfn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(asfn(*args, **kwargs))


async def forall_in_q(db: Database, q, fn):
    proxy = db.iterate(query=q)
    #print(proxy.description)
    async for row in proxy:
        await fn(row._mapping)


# Queries
def all_messages_q():
    return tables.messages.select()


# Demos
async def show_messages(db: Database):
    q = all_messages_q()
    await forall_in_q(db, q, print)


if __name__ == "__main__":
    from spchat.db.sessionlocal import database
    test_coroutine(show_messages, database)

    all_messages_q()
