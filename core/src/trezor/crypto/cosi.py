from typing import TYPE_CHECKING

from .curve import ed25519

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Sequence


commit = ed25519.cosi_commit
sign = ed25519.cosi_sign
combine_publickeys = ed25519.cosi_combine_publickeys
combine_signatures = ed25519.cosi_combine_signatures


def select_keys(sigmask: int, keys: Sequence[AnyBytes]) -> list[AnyBytes]:
    selected_keys = []
    for key in keys:
        if sigmask & 1:
            selected_keys.append(key)
        sigmask >>= 1
    if sigmask:
        raise ValueError  # sigmask specifies more public keys than provided
    return selected_keys


def verify(
    signature: AnyBytes,
    data: AnyBytes,
    threshold: int,
    keys: Sequence[AnyBytes],
    sigmask: int,
) -> bool:
    if threshold < 1:
        raise ValueError  # at least one signer is required

    selected_keys = select_keys(sigmask, keys)
    if len(selected_keys) < threshold:
        return False  # insufficient number of signatures

    global_pk = combine_publickeys(selected_keys)
    return ed25519.verify(global_pk, signature, data)
