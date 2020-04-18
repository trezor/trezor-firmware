from trezor.messages import MessageType

if __debug__:
    from trezor import log

if False:
    from typing import Dict, Type  # noqa: F401
    from protobuf import MessageType as MessageType_  # noqa: F401

    MessageClass = Type[MessageType_]

type_to_name = {}  # type: Dict[int, str]  # reverse table of wire_type mapping
registered = {}  # type: Dict[int, MessageClass]  # dynamically registered types


def register(msg_type: MessageClass) -> None:
    """Register custom message type in runtime."""
    if __debug__:
        log.debug(__name__, "register %s", msg_type)
    registered[msg_type.MESSAGE_WIRE_TYPE] = msg_type


def get_type(wire_type: int) -> MessageClass:
    """Get message class for handling given wire_type."""
    if wire_type in registered:
        # message class is explicitly registered
        msg_type = registered[wire_type]
    else:
        # import message class from trezor.messages dynamically
        name = type_to_name[wire_type]
        module = __import__("trezor.messages.%s" % name, None, None, (name,), 0)
        msg_type = getattr(module, name)
    return msg_type


# build reverse table of wire types
for msg_name in dir(MessageType):
    # Modules contain internal variables that may cause exception here.
    # No Message begins with underscore so it's safe to skip those.
    if msg_name[0] == "_":
        continue
    if msg_name == "utils":  # skip imported trezor.utils
        continue
    type_to_name[getattr(MessageType, msg_name)] = msg_name
