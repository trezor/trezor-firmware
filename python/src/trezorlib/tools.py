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

from __future__ import annotations

import functools
import hashlib
import re
import struct
import typing as t
import unicodedata
from contextlib import AbstractContextManager
from enum import Enum

import construct
import typing_extensions as tx

from . import messages

P = tx.ParamSpec("P")
R = t.TypeVar("R")
C = t.TypeVar("C")
CM = t.TypeVar("CM", bound=AbstractContextManager)

if t.TYPE_CHECKING:
    from .client import Session

    SessionFunc = t.Callable[tx.Concatenate[Session, P], R]
    ContextFunc = t.Callable[tx.Concatenate[CM, P], R]

HARDENED_FLAG = 1 << 31

Address = t.NewType("Address", list[int])


def H_(x: int) -> int:
    """
    Shortcut function that "hardens" a number in a BIP44 path.
    """
    return x | HARDENED_FLAG


def is_hardened(x: int) -> bool:
    """
    Determines if a number in a BIP44 path is hardened.
    """
    return x & HARDENED_FLAG != 0


def unharden(x: int) -> int:
    """
    Unhardens a number in a BIP44 path.
    """
    if not is_hardened(x):
        raise ValueError("Unhardened path component")

    return x ^ HARDENED_FLAG


def btc_hash(data: bytes) -> bytes:
    """
    Double-SHA256 hash as used in BTC
    """
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def tx_hash(data: bytes) -> bytes:
    """Calculate and return double-SHA256 hash in reverse order.

    This is what Bitcoin uses as txids.
    """
    return btc_hash(data)[::-1]


def hash_160(public_key: bytes) -> bytes:
    md = hashlib.new("ripemd160")
    md.update(hashlib.sha256(public_key).digest())
    return md.digest()


def hash_160_to_bc_address(h160: bytes, address_type: int) -> str:
    vh160 = struct.pack("<B", address_type) + h160
    h = btc_hash(vh160)
    addr = vh160 + h[0:4]
    return b58encode(addr)


def compress_pubkey(public_key: bytes) -> bytes:
    if public_key[0] == 4:
        return bytes((public_key[64] & 1) + 2) + public_key[1:33]
    raise ValueError("Pubkey is already compressed")


def public_key_to_bc_address(
    public_key: bytes, address_type: int, compress: bool = True
) -> str:
    if public_key[0] == "\x04" and compress:
        public_key = compress_pubkey(public_key)

    h160 = hash_160(public_key)
    return hash_160_to_bc_address(h160, address_type)


__b58chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
__b58base = len(__b58chars)


def b58encode_int(i: int) -> str:
    """Encode an integer using Base58"""
    digits = []
    while i:
        i, idx = divmod(i, __b58base)
        digits.append(__b58chars[idx])
    return "".join(reversed(digits))


def b58encode(v: bytes) -> str:
    """encode v, which is a string of bytes, to base58."""
    origlen = len(v)
    v = v.lstrip(b"\0")
    newlen = len(v)

    acc = int.from_bytes(v, byteorder="big")  # first byte is most significant

    result = b58encode_int(acc)
    return __b58chars[0] * (origlen - newlen) + result


def b58decode_int(v: str) -> int:
    """Decode a Base58 encoded string as an integer"""
    decimal = 0
    try:
        for char in v:
            decimal = decimal * __b58base + __b58chars.index(char)
    except KeyError:
        raise ValueError(f"Invalid character {char!r}") from None
    return decimal


def b58decode(v: t.AnyStr, length: int | None = None) -> bytes:
    """decode v into a string of len bytes."""
    v_str = v if isinstance(v, str) else v.decode()
    origlen = len(v_str)
    v_str = v_str.lstrip(__b58chars[0])
    newlen = len(v_str)

    acc = b58decode_int(v_str)

    result = acc.to_bytes(origlen - newlen + (acc.bit_length() + 7) // 8, "big")
    if length is not None and len(result) != length:
        raise ValueError("Result length does not match expected_length")

    return result


def b58check_encode(v: bytes) -> str:
    checksum = btc_hash(v)[:4]
    return b58encode(v + checksum)


def b58check_decode(v: t.AnyStr, length: int | None = None) -> bytes:
    dec = b58decode(v, length)
    data, checksum = dec[:-4], dec[-4:]
    if btc_hash(data)[:4] != checksum:
        raise ValueError("invalid checksum")
    return data


def parse_path(nstr: str) -> Address:
    """
    Convert BIP32 path string to list of uint32 integers with hardened flags.
    Several conventions are supported to set the hardened flag: -1, 1', 1h

    e.g.: "0/1h/1" -> [0, 0x80000001, 1]

    :param nstr: path string
    :return: list of integers
    """
    if not nstr:
        return Address([])

    n = nstr.split("/")

    # m/a/b/c => a/b/c
    if n[0] == "m":
        n = n[1:]

    def str_to_harden(x: str) -> int:
        if x.startswith("-"):
            return H_(abs(int(x)))
        elif x.endswith(("h", "'")):
            return H_(int(x[:-1]))
        else:
            return int(x)

    try:
        return Address([str_to_harden(x) for x in n])
    except Exception as e:
        raise ValueError("Invalid BIP32 path", nstr) from e


def format_path(path: Address, flag: str = "h") -> str:
    """
    Convert BIP32 path list of uint32 integers with hardened flags to string.
    Several conventions are supported to denote the hardened flag: 1', 1h

    e.g.: [0, 0x80000001, 1] -> "m/0/1h/1"

    :param path: list of integers
    :return: path string
    """
    nstr = "m"
    for i in path:
        nstr += f"/{unharden(i)}{flag if is_hardened(i) else ''}"

    return nstr


def prepare_message_bytes(txt: t.AnyStr) -> bytes:
    """
    Make message suitable for protobuf.
    If the message is a Unicode string, normalize it.
    If it's bytes, return the raw bytes.
    """
    if isinstance(txt, bytes):
        return txt
    return unicodedata.normalize("NFC", txt).encode()


# de-camelcasifier
# https://stackoverflow.com/a/1176023/222189

FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


def from_camelcase(s: str) -> str:
    s = FIRST_CAP_RE.sub(r"\1_\2", s)
    return ALL_CAP_RE.sub(r"\1_\2", s).lower()


def dict_from_camelcase(
    d: t.Any, renames: dict[str, str] | None = None
) -> dict[str, t.Any]:
    if not isinstance(d, dict):
        return d

    if renames is None:
        renames = {}

    res = {}
    for key, value in d.items():
        newkey = from_camelcase(key)
        renamed_key = renames.get(newkey) or renames.get(key)
        if renamed_key:
            newkey = renamed_key

        if isinstance(value, list):
            res[newkey] = [dict_from_camelcase(v, renames) for v in value]
        else:
            res[newkey] = dict_from_camelcase(value, renames)

    return res


# adapted from https://github.com/bitcoin-core/HWI/blob/master/hwilib/descriptor.py


def descriptor_checksum(desc: str) -> str:
    def _polymod(c: int, val: int) -> int:
        c0 = c >> 35
        c = ((c & 0x7FFFFFFFF) << 5) ^ val
        if c0 & 1:
            c ^= 0xF5DEE51989
        if c0 & 2:
            c ^= 0xA9FDCA3312
        if c0 & 4:
            c ^= 0x1BAB10E32D
        if c0 & 8:
            c ^= 0x3706B1677A
        if c0 & 16:
            c ^= 0x644D626FFD
        return c

    INPUT_CHARSET = "0123456789()[],'/*abcdefgh@:$%{}IJKLMNOPQRSTUVWXYZ&+-.;<=>?!^_|~ijklmnopqrstuvwxyzABCDEFGH`#\"\\ "
    CHECKSUM_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    c = 1
    cls = 0
    clscount = 0
    for ch in desc:
        pos = INPUT_CHARSET.find(ch)
        if pos == -1:
            return ""
        c = _polymod(c, pos & 31)
        cls = cls * 3 + (pos >> 5)
        clscount += 1
        if clscount == 3:
            c = _polymod(c, cls)
            cls = 0
            clscount = 0
    if clscount > 0:
        c = _polymod(c, cls)
    for j in range(0, 8):
        c = _polymod(c, 0)
    c ^= 1

    ret = [""] * 8
    for j in range(0, 8):
        ret[j] = CHECKSUM_CHARSET[(c >> (5 * (7 - j))) & 31]
    return "".join(ret)


class EnumAdapter(construct.Adapter):
    def __init__(self, subcon: construct.Adapter, enum: type[Enum]) -> None:
        self.enum = enum
        super().__init__(subcon)

    def _encode(self, obj: t.Any, context: t.Any, path: t.Any) -> t.Any:
        if isinstance(obj, self.enum):
            return obj.value
        return obj

    def _decode(self, obj: t.Any, context: t.Any, path: t.Any) -> t.Any:
        try:
            return self.enum(obj)
        except ValueError:
            return obj


class TupleAdapter(construct.Adapter):
    def __init__(self, *subcons: construct.Adapter) -> None:
        super().__init__(construct.Sequence(*subcons))

    def _encode(self, obj: t.Any, context: t.Any, path: t.Any) -> t.Any:
        return obj

    def _decode(self, obj: t.Any, context: t.Any, path: t.Any) -> t.Any:
        return tuple(obj)


def enter_context(context_func: ContextFunc[CM, P, R]) -> ContextFunc[CM, P, R]:
    """Generic wrapper around any function or method that accepts a context manager
    as its first argument.

    The function will run inside the context.
    """

    @functools.wraps(context_func)
    def wrapper(context: CM, *args: P.args, **kwargs: P.kwargs) -> R:
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        with context:
            return context_func(context, *args, **kwargs)

    return wrapper


class workflow(t.Generic[P, R]):
    """Trezor workflow call decorator.

    Functionally, keeps a connection open between steps of the workflow.
    Can also carry metadata about supported Trezor version and required capabilities.
    """

    def __init__(
        self,
        *,
        from_version: tuple[int, int, int] | None = None,
        capability: messages.Capability | None = None,
        capabilities: set[messages.Capability] | None = None,
    ) -> None:
        self.from_version = from_version
        if capability is not None and capabilities is not None:
            raise ValueError("Cannot specify both capability and capabilities")
        if capability is not None:
            capabilities = {capability}
        elif capabilities is None:
            capabilities = set()
        self.capabilities = capabilities
        self.func: SessionFunc[P, R] | None = None

    def __call__(self, func: SessionFunc[P, R]) -> SessionFunc[P, R]:
        self.func = func
        return self.wrapper

    def wrapper(self, session: Session, *args: P.args, **kwargs: P.kwargs) -> R:
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        if self.func is None:
            raise RuntimeError("workflow decorator must be used with a function")
        with session:
            return self.func(session, *args, **kwargs)
