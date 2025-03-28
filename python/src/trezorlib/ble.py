import typing as t

from . import messages
from .tools import session

if t.TYPE_CHECKING:
    from ..client import TrezorClient


@session
def unpair(
    client: "TrezorClient",
    all: bool,
):

    resp = client.call(messages.BleUnpair(all=all))

    if isinstance(resp, messages.Success):
        return
    else:
        raise RuntimeError(f"Unexpected message {resp}")
