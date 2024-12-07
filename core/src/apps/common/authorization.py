from typing import Iterable

from storage.cache_common import (
    APP_COMMON_AUTHORIZATION_DATA,
    APP_COMMON_AUTHORIZATION_TYPE,
)
from trezor import protobuf
from trezor.enums import MessageType
from trezor.wire import context

WIRE_TYPES: dict[int, tuple[int, ...]] = {
    MessageType.AuthorizeCoinJoin: (MessageType.SignTx, MessageType.GetOwnershipProof),
}


def is_set() -> bool:
    return context.cache_get(APP_COMMON_AUTHORIZATION_TYPE) is not None


def set(auth_message: protobuf.MessageType) -> None:
    from trezor.utils import ensure

    buffer = protobuf.dump_message_buffer(auth_message)

    # only wire-level messages can be stored as authorization
    # (because only wire-level messages have wire_type, which we use as identifier)
    ensure(auth_message.MESSAGE_WIRE_TYPE is not None)
    assert auth_message.MESSAGE_WIRE_TYPE is not None  # so that typechecker knows too
    context.cache_set_int(APP_COMMON_AUTHORIZATION_TYPE, auth_message.MESSAGE_WIRE_TYPE)
    context.cache_set(APP_COMMON_AUTHORIZATION_DATA, buffer)


def get() -> protobuf.MessageType | None:
    stored_auth_type = context.cache_get_int(APP_COMMON_AUTHORIZATION_TYPE)
    if not stored_auth_type:
        return None

    buffer = context.cache_get(APP_COMMON_AUTHORIZATION_DATA, b"")
    return protobuf.load_message_buffer(buffer, stored_auth_type)


def is_set_any_session(auth_type: MessageType) -> bool:
    return auth_type in context.cache_get_int_all_sessions(
        APP_COMMON_AUTHORIZATION_TYPE
    )


def get_wire_types() -> Iterable[int]:
    stored_auth_type = context.cache_get_int(APP_COMMON_AUTHORIZATION_TYPE)
    if stored_auth_type is None:
        return ()

    return WIRE_TYPES.get(stored_auth_type, ())


def clear() -> None:
    context.cache_delete(APP_COMMON_AUTHORIZATION_TYPE)
    context.cache_delete(APP_COMMON_AUTHORIZATION_DATA)
