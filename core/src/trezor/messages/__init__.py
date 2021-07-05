if False:
    import protobuf
    from typing import Type


def get_type(wire_type: int) -> Type[protobuf.MessageType]:
    """Get message class for handling given wire_type."""
    from trezor.messages import MessageType

    for msg_name in dir(MessageType):
        # walk the list of symbols in MessageType
        if getattr(MessageType, msg_name) == wire_type:
            # import submodule/class of the same name
            module = __import__(
                "trezor.messages.%s" % msg_name, None, None, (msg_name,), 0
            )
            return getattr(module, msg_name)  # type: ignore

    raise KeyError
