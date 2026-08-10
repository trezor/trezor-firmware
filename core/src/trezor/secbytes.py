"""Marking of secret values for the type checker.

`secure[T]` (declared in `mocks/buffer_types.pyi`, with the `securebytes` and
`securestr` aliases) is a hint and nothing else: no runtime type, no separate
allocation, no wiping on destruction. Its only job is to make the checker
reject the accidental uses of a secret -- slicing it, concatenating it,
encoding it, handing it to a function that takes a public value -- and to make
our handling of secrets greppable.

The two functions below are the identity at runtime. `classify` marks a value
on the way in, `declassify` unmarks it on the way out; the set of `declassify`
call sites is the list of points where a secret leaves the tracked domain.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import StrOrBytes, secure
    from typing import TypeVar

    S = TypeVar("S", bound=StrOrBytes)


def classify(data: S) -> secure[S]:
    """Mark `data` as holding secret material.

    Call it where a secret first enters Python -- a PIN or passphrase typed by
    the user, a mnemonic read from storage, a derived seed.
    """
    return data  # type: ignore [Type "S@classify" is not assignable to return type "secure[S@classify]"]


def declassify(data: secure[S]) -> S:
    """Drop the secret marking, yielding the plain value.

    Every call is a place where a secret stops being tracked, typically a call
    into `trezorconfig` or `trezorcrypto`. Keep the result short-lived: pass it
    inline at the call site rather than binding it to a long-scoped name.
    """
    return data  # type: ignore [Type "secure[S@declassify]" is not assignable to return type "S@declassify"]


EMPTY_SECURESTR = classify("")
"""The empty secret string.

Use it as the default for an optional PIN/passphrase parameter, so that the
parameter can stay plain `securestr` instead of `securestr | None`, and the
body does not need to special-case "not given".
"""
