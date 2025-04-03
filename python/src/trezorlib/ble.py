import typing as t

from . import messages

if t.TYPE_CHECKING:
    from .transport.session import Session


def unpair(
    session: "Session",
    all: bool,
):

    resp = session.call(messages.BleUnpair(all=all))

    if isinstance(resp, messages.Success):
        return
    else:
        raise RuntimeError(f"Unexpected message {resp}")
