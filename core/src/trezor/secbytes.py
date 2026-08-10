from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes, securebytes


def classify(data: AnyBytes) -> securebytes:
    """Mark `data` as holding secret material.

    Call it where a secret first enters Python -- a mnemonic read from
    storage, a passphrase received from the host, a derived seed.
    """
    return data  # type: ignore [Type "AnyBytes" is not assignable to return type "securebytes"]


def declassify(data: securebytes) -> AnyBytes:
    """Drop the secret marking, yielding a plain buffer.

    Every call is a place where a secret stops being tracked, typically a
    call into `trezorcrypto`. Keep the result short-lived: assign it inline
    at the call site rather than binding it to a long-scoped name.
    """
    return data  # type: ignore [Type "securebytes" is not assignable to return type "AnyBytes"]
