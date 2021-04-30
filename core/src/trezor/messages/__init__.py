from trezorutils import protobuf_type_for_name

from trezor.enums import MessageType

if __debug__:
    from trezor import log

if False:
    from protobuf import MessageType as MessageType_  # noqa: F401

    MessageClass = type[MessageType_]


def __getattr__(name):
    try:
        return protobuf_type_for_name(name)
    except ValueError:
        # TODO: Import all enums from `trezor.enums` directly and remove this.
        return __import__("trezor.enums.%s" % name, None, None, (name,), 0)
