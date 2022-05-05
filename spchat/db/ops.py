from spchat.db.sessionlocal import tables
from spchat.db.models import MessageIn


def insert_msg_op(msg: MessageIn):
    return tables.messages.insert().values(
        user_from=msg.user_from,
        at=msg.at,
        chat_message=msg.chat_message,
    )
