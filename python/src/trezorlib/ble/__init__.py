import typing as t

from .. import messages
from ..tools import session

if t.TYPE_CHECKING:
    from ..client import TrezorClient


@session
def update(
    client: "TrezorClient",
    datfile: bytes,
    binfile: bytes,
    progress_update: t.Callable[[int], t.Any] = lambda _: None,
):
    chunk_len = 4096
    offset = 0

    resp = client.call(
        messages.UploadBLEFirmwareInit(init_data=datfile, binsize=len(binfile))
    )

    while isinstance(resp, messages.UploadBLEFirmwareNextChunk):

        payload = binfile[offset : offset + chunk_len]
        resp = client.call(messages.UploadBLEFirmwareChunk(data=payload))
        progress_update(chunk_len)
        offset += chunk_len

    if isinstance(resp, messages.Success):
        return
    else:
        raise RuntimeError(f"Unexpected message {resp}")


@session
def erase_bonds(
    client: "TrezorClient",
):

    resp = client.call(messages.EraseBonds())

    if isinstance(resp, messages.Success):
        return
    else:
        raise RuntimeError(f"Unexpected message {resp}")


@session
def unpair(
    client: "TrezorClient",
):

    resp = client.call(messages.Unpair())

    if isinstance(resp, messages.Success):
        return
    else:
        raise RuntimeError(f"Unexpected message {resp}")


@session
def disconnect(
    client: "TrezorClient",
):
    resp = client.call(messages.Disconnect())

    if isinstance(resp, messages.Success):
        return
    else:
        raise RuntimeError(f"Unexpected message {resp}")
