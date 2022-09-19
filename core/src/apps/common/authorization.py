from typing import Iterable

import storage.cache as storage_cache
from trezor import protobuf
from trezor.enums import MessageType

WIRE_TYPES: dict[int, tuple[int, ...]] = {
    MessageType.AuthorizeCoinJoin: (MessageType.SignTx, MessageType.GetOwnershipProof),
}

APP_COMMON_AUTHORIZATION_DATA = (
    storage_cache.APP_COMMON_AUTHORIZATION_DATA
)  # global_import_cache
APP_COMMON_AUTHORIZATION_TYPE = (
    storage_cache.APP_COMMON_AUTHORIZATION_TYPE
)  # global_import_cache


def is_set() -> bool:
    return bool(storage_cache.get(APP_COMMON_AUTHORIZATION_TYPE))


def set(auth_message: protobuf.MessageType) -> None:
    from trezor.utils import ensure

    buffer = protobuf.dump_message_buffer(auth_message)

    # only wire-level messages can be stored as authorization
    # (because only wire-level messages have wire_type, which we use as identifier)
    ensure(auth_message.MESSAGE_WIRE_TYPE is not None)
    assert auth_message.MESSAGE_WIRE_TYPE is not None  # so that typechecker knows too
    storage_cache.set(
        APP_COMMON_AUTHORIZATION_TYPE,
        auth_message.MESSAGE_WIRE_TYPE.to_bytes(2, "big"),
    )
    storage_cache.set(APP_COMMON_AUTHORIZATION_DATA, buffer)


def get() -> protobuf.MessageType | None:
    stored_auth_type = storage_cache.get(APP_COMMON_AUTHORIZATION_TYPE)
    if not stored_auth_type:
        return None

    msg_wire_type = int.from_bytes(stored_auth_type, "big")
    buffer = storage_cache.get(APP_COMMON_AUTHORIZATION_DATA, b"")
    return protobuf.load_message_buffer(buffer, msg_wire_type)


def get_wire_types() -> Iterable[int]:
    stored_auth_type = storage_cache.get(APP_COMMON_AUTHORIZATION_TYPE)
    if stored_auth_type is None:
        return ()

    msg_wire_type = int.from_bytes(stored_auth_type, "big")
    return WIRE_TYPES.get(msg_wire_type, ())


def clear() -> None:
    storage_cache.delete(APP_COMMON_AUTHORIZATION_TYPE)
    storage_cache.delete(APP_COMMON_AUTHORIZATION_DATA)
