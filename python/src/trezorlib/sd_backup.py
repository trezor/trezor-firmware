from typing import TYPE_CHECKING
from . import messages
from .tools import expect, session

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType


@expect(messages.SdCardBackupHealth)
@session
def check(client: "TrezorClient") -> "MessageType":
    return client.call(
        messages.SdCardBackupManage(operation=messages.SdCardBackupManageOperationType.CHECK)
    )

@expect(messages.Success)
@session
def refresh(client: "TrezorClient") -> "MessageType":
    return client.call(
        messages.SdCardBackupManage(operation=messages.SdCardBackupManageOperationType.REFRESH)
    )

@expect(messages.Success)
@session
def wipe(client: "TrezorClient") -> "MessageType":
    return client.call(
        messages.SdCardBackupManage(operation=messages.SdCardBackupManageOperationType.WIPE)
    )

@expect(messages.Success)
@session
def copy(client: "TrezorClient") -> "MessageType":
    return client.call(
        messages.SdCardBackupManage(operation=messages.SdCardBackupManageOperationType.COPY)
    )
