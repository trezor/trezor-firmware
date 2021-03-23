import storage.cache
from trezor import protobuf
from trezor.enums import MessageType
from trezor.utils import ensure

if False:
    from typing import Iterable

WIRE_TYPES: dict[int, tuple[int, ...]] = {
    MessageType.AuthorizeCoinJoin: (MessageType.SignTx, MessageType.GetOwnershipProof),
}


def is_set() -> bool:
    return bool(storage.cache.get(storage.cache.APP_COMMON_AUTHORIZATION_TYPE))


def set(auth_message: protobuf.MessageType) -> None:
    buffer = protobuf.dump_message_buffer(auth_message)

    # only wire-level messages can be stored as authorization
    # (because only wire-level messages have wire_type, which we use as identifier)
    ensure(auth_message.MESSAGE_WIRE_TYPE is not None)
    assert auth_message.MESSAGE_WIRE_TYPE is not None  # so that mypy knows as well
    storage.cache.set(
        storage.cache.APP_COMMON_AUTHORIZATION_TYPE,
        auth_message.MESSAGE_WIRE_TYPE.to_bytes(2, "big"),
    )
    storage.cache.set(storage.cache.APP_COMMON_AUTHORIZATION_DATA, buffer)


def get() -> protobuf.MessageType | None:
    stored_auth_type = storage.cache.get(storage.cache.APP_COMMON_AUTHORIZATION_TYPE)
    if not stored_auth_type:
        return None

    msg_wire_type = int.from_bytes(stored_auth_type, "big")
    buffer = storage.cache.get(storage.cache.APP_COMMON_AUTHORIZATION_DATA)
    return protobuf.load_message_buffer(buffer, msg_wire_type)


def get_wire_types() -> Iterable[int]:
    stored_auth_type = storage.cache.get(storage.cache.APP_COMMON_AUTHORIZATION_TYPE)
    if not stored_auth_type:
        return ()

    msg_wire_type = int.from_bytes(stored_auth_type, "big")
    return WIRE_TYPES.get(msg_wire_type, ())


def clear() -> None:
    storage.cache.set(storage.cache.APP_COMMON_AUTHORIZATION_TYPE, b"")
    storage.cache.set(storage.cache.APP_COMMON_AUTHORIZATION_DATA, b"")
