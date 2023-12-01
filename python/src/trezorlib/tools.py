# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import functools
import hashlib
import re
import struct
import unicodedata
from typing import (
    TYPE_CHECKING,
    Any,
    AnyStr,
    Callable,
    Dict,
    List,
    NewType,
    Optional,
    Type,
    Union,
    overload,
)

import construct

if TYPE_CHECKING:
    # Needed to enforce a return value from decorators
    # More details: https://www.python.org/dev/peps/pep-0612/
    from typing import TypeVar

    from typing_extensions import Concatenate, ParamSpec

    from .client import TrezorClient
    from .protobuf import MessageType

    MT = TypeVar("MT", bound=MessageType)
    P = ParamSpec("P")
    R = TypeVar("R")

HARDENED_FLAG = 1 << 31

Address = NewType("Address", List[int])


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
        raise ValueError(f"Invalid character {char!r}") from None  # type: ignore [possibly unbound]
    return decimal


def b58decode(v: AnyStr, length: Optional[int] = None) -> bytes:
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


def b58check_decode(v: AnyStr, length: Optional[int] = None) -> bytes:
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


def prepare_message_bytes(txt: AnyStr) -> bytes:
    """
    Make message suitable for protobuf.
    If the message is a Unicode string, normalize it.
    If it's bytes, return the raw bytes.
    """
    if isinstance(txt, bytes):
        return txt
    return unicodedata.normalize("NFC", txt).encode()


# NOTE for type tests (mypy/pyright):
# Overloads below have a goal of enforcing the return value
# that should be returned from the original function being decorated
# while still preserving the function signature (the inputted arguments
# are going to be type-checked).
# Currently (November 2021) mypy does not support "ParamSpec" typing
# construct, so it will not understand it and will complain about
# definitions below.


@overload
def expect(
    expected: "Type[MT]",
) -> "Callable[[Callable[P, MessageType]], Callable[P, MT]]":
    ...


@overload
def expect(
    expected: "Type[MT]", *, field: str, ret_type: "Type[R]"
) -> "Callable[[Callable[P, MessageType]], Callable[P, R]]":
    ...


def expect(
    expected: "Type[MT]",
    *,
    field: Optional[str] = None,
    ret_type: "Optional[Type[R]]" = None,
) -> "Callable[[Callable[P, MessageType]], Callable[P, Union[MT, R]]]":
    """
    Decorator checks if the method
    returned one of expected protobuf messages
    or raises an exception
    """

    def decorator(f: "Callable[P, MessageType]") -> "Callable[P, Union[MT, R]]":
        @functools.wraps(f)
        def wrapped_f(*args: "P.args", **kwargs: "P.kwargs") -> "Union[MT, R]":
            __tracebackhide__ = True  # for pytest # pylint: disable=W0612
            ret = f(*args, **kwargs)
            if not isinstance(ret, expected):
                raise RuntimeError(f"Got {ret.__class__}, expected {expected}")
            if field is not None:
                return getattr(ret, field)
            else:
                return ret

        return wrapped_f

    return decorator


def session(
    f: "Callable[Concatenate[TrezorClient, P], R]",
) -> "Callable[Concatenate[TrezorClient, P], R]":
    # Decorator wraps a BaseClient method
    # with session activation / deactivation
    @functools.wraps(f)
    def wrapped_f(client: "TrezorClient", *args: "P.args", **kwargs: "P.kwargs") -> "R":
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        client.open()
        try:
            return f(client, *args, **kwargs)
        finally:
            client.close()

    return wrapped_f


# de-camelcasifier
# https://stackoverflow.com/a/1176023/222189

FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


def from_camelcase(s: str) -> str:
    s = FIRST_CAP_RE.sub(r"\1_\2", s)
    return ALL_CAP_RE.sub(r"\1_\2", s).lower()


def dict_from_camelcase(d: Any, renames: Optional[dict] = None) -> dict:
    if not isinstance(d, dict):
        return d

    if renames is None:
        renames = {}

    res: Dict[str, Any] = {}
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
    def __init__(self, subcon: Any, enum: Any) -> None:
        self.enum = enum
        super().__init__(subcon)

    def _encode(self, obj: Any, ctx: Any, path: Any):
        if isinstance(obj, self.enum):
            return obj.value
        return obj

    def _decode(self, obj: Any, ctx: Any, path: Any):
        try:
            return self.enum(obj)
        except ValueError:
            return obj


class TupleAdapter(construct.Adapter):
    def __init__(self, *subcons: Any) -> None:
        super().__init__(construct.Sequence(*subcons))

    def _encode(self, obj: Any, ctx: Any, path: Any):
        return obj

    def _decode(self, obj: Any, ctx: Any, path: Any):
        return tuple(obj)
