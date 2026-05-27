"""Namecoin name-operation script construction.

This module builds the OP_* + OP_DROP prelude that Namecoin consensus
(`namecoin-core/src/script/names.cpp`, CNameScript) prepends to an
otherwise-standard P2PKH or P2SH output script for the three name-op
kinds:

  * NAME_NEW          OP_1  <push 20-byte commitment_hash> OP_2DROP <addr_script>
  * NAME_FIRSTUPDATE  OP_2  <push name> <push rand> <push value>
                            OP_2DROP OP_2DROP OP_DROP <addr_script>
  * NAME_UPDATE       OP_3  <push name> <push value>
                            OP_2DROP OP_DROP <addr_script>

The functions in this module only construct the prelude + concatenated
inner address script. They never parse on-device: the device always
receives a structured NamecoinOp protobuf message from the host and
builds the script from those fields, so there is no name-op parser
here.

Length limits are enforced per ifa-0001 (Namecoin's name-handling spec):
the name is at most 255 bytes and the value at most 520 bytes; both are
raw bytes whose semantic encoding is the host's responsibility. The
commitment hash and rand nonce are exactly 20 bytes (HASH160).
"""

from micropython import const
from typing import TYPE_CHECKING

from trezor import utils
from trezor.wire import DataError

from .writers import write_op_push

if TYPE_CHECKING:
    from buffer_types import AnyBytes


_OP_1 = const(0x51)
_OP_2 = const(0x52)
_OP_3 = const(0x53)
_OP_DROP = const(0x75)
_OP_2DROP = const(0x6D)

_NAME_MAX = const(255)
_VALUE_MAX = const(520)
_HASH_LEN = const(20)


def _push_length(n: int) -> int:
    # 1 byte for n<0x4c, 2 bytes for n<0x100, 3 bytes for n<0x10000.
    if n < 0x4C:
        return 1
    elif n < 0x100:
        return 2
    else:
        return 3


def _append_push(buf: bytearray, data: AnyBytes) -> None:
    write_op_push(buf, len(data))
    buf.extend(data)


def output_script_name_new(
    commitment_hash: AnyBytes, address_script: AnyBytes
) -> bytes:
    """Build the scriptPubKey for a NAME_NEW output.

    Layout: OP_1 <push20 commitment_hash> OP_2DROP <address_script>.
    """
    if len(commitment_hash) != _HASH_LEN:
        raise DataError("name_new commitment_hash must be 20 bytes")

    # 1 (OP_1) + 1 (push20) + 20 (hash) + 1 (OP_2DROP) + len(address_script)
    size = 3 + _HASH_LEN + len(address_script)
    w = utils.empty_bytearray(size)
    w.append(_OP_1)
    _append_push(w, commitment_hash)
    w.append(_OP_2DROP)
    w.extend(address_script)
    return bytes(w)


def output_script_name_firstupdate(
    name: AnyBytes,
    rand: AnyBytes,
    value: AnyBytes,
    address_script: AnyBytes,
) -> bytes:
    """Build the scriptPubKey for a NAME_FIRSTUPDATE output.

    Layout: OP_2 <push name> <push rand> <push value>
            OP_2DROP OP_2DROP OP_DROP <address_script>.
    """
    if not 1 <= len(name) <= _NAME_MAX:
        raise DataError("name_firstupdate name length out of range")
    if len(rand) != _HASH_LEN:
        raise DataError("name_firstupdate rand must be 20 bytes")
    if len(value) > _VALUE_MAX:
        raise DataError("name_firstupdate value too long")

    size = (
        1  # OP_2
        + _push_length(len(name))
        + len(name)
        + _push_length(len(rand))
        + len(rand)
        + _push_length(len(value))
        + len(value)
        + 3  # OP_2DROP OP_2DROP OP_DROP
        + len(address_script)
    )
    w = utils.empty_bytearray(size)
    w.append(_OP_2)
    _append_push(w, name)
    _append_push(w, rand)
    _append_push(w, value)
    w.append(_OP_2DROP)
    w.append(_OP_2DROP)
    w.append(_OP_DROP)
    w.extend(address_script)
    return bytes(w)


def output_script_name_update(
    name: AnyBytes, value: AnyBytes, address_script: AnyBytes
) -> bytes:
    """Build the scriptPubKey for a NAME_UPDATE output.

    Layout: OP_3 <push name> <push value>
            OP_2DROP OP_DROP <address_script>.
    """
    if not 1 <= len(name) <= _NAME_MAX:
        raise DataError("name_update name length out of range")
    if len(value) > _VALUE_MAX:
        raise DataError("name_update value too long")

    size = (
        1  # OP_3
        + _push_length(len(name))
        + len(name)
        + _push_length(len(value))
        + len(value)
        + 2  # OP_2DROP OP_DROP
        + len(address_script)
    )
    w = utils.empty_bytearray(size)
    w.append(_OP_3)
    _append_push(w, name)
    _append_push(w, value)
    w.append(_OP_2DROP)
    w.append(_OP_DROP)
    w.extend(address_script)
    return bytes(w)
