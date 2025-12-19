# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.
"""
CPace, a balanced composable PAKE: https://datatracker.ietf.org/doc/draft-irtf-cfrg-cpace/
"""

from __future__ import annotations

import secrets
import typing as t
from hashlib import sha512

from . import curve25519

DSI = b"CPace255"
HASH_BLOCK_SIZE = sha512().block_size
FIELD_SIZE_BYTES = 32


class CpaceResult(t.NamedTuple):
    """Result of a CPace exchange."""

    a_pubkey: bytes
    """Public key of the initiator, to be sent to the counterparty."""
    shared_secret: bytes
    """Shared secret, to be used for further communication."""


def _leb128(value: int) -> bytes:
    if value > 0x7F:
        raise NotImplementedError
    return value.to_bytes(1, "little")


def _prepend_len(data: bytes) -> bytes:
    return _leb128(len(data)) + data


def _lv_cat(*args: bytes) -> bytes:
    return b"".join(_prepend_len(arg) for arg in args)


def _generator_string(
    *,
    prs: bytes,
    ci: bytes,
    sid: bytes = b"",
) -> bytes:
    dsi_bytes = _prepend_len(DSI)
    prs_bytes = _prepend_len(prs)
    len_zpad = max(0, HASH_BLOCK_SIZE - (len(dsi_bytes) + len(prs_bytes) + 1))
    return _lv_cat(DSI, prs, b"\x00" * len_zpad, ci, sid)


def _generator(prs: bytes, ci: bytes, sid: bytes = b"") -> bytes:
    gen_str = _generator_string(prs=prs, ci=ci, sid=sid)
    gen_str_hashed = sha512(gen_str).digest()[:FIELD_SIZE_BYTES]
    return curve25519.elligator2(gen_str_hashed)


def cpace(
    *,
    prs: bytes,
    ci: bytes,
    sid: bytes = b"",
    b_pubkey: bytes,
    _a_privkey: bytes | None = None,
) -> CpaceResult:
    """Perform the CPace255 protocol.

    That is, an instance of CPace for group object G_X25519.

    Detailed specification is available at https://datatracker.ietf.org/doc/draft-irtf-cfrg-cpace/,
    argument names match the specification.

    Arguments:
        prs: Possibly low-entropy shared passphrase.
        ci: Channel identifier that binds both participantsto the current communication channel.
        sid: Optional session identifier.
        b_pubkey: Public key of the counterparty.

    Returns: the result of the CPace protocol. See `CpaceResult` for details.
    """
    generator = _generator(prs=prs, ci=ci, sid=sid)
    if _a_privkey is not None:
        a_privkey = _a_privkey
    else:
        a_privkey = secrets.token_bytes(FIELD_SIZE_BYTES)
    a_pubkey = curve25519.multiply(a_privkey, generator)
    shared_secret = curve25519.multiply(a_privkey, b_pubkey)
    return CpaceResult(a_pubkey=a_pubkey, shared_secret=shared_secret)
