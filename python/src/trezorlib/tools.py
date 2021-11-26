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

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType

    # Needed to enforce a return value from decorators
    # More details: https://www.python.org/dev/peps/pep-0612/
    from typing import TypeVar
    from typing_extensions import ParamSpec, Concatenate

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


def b58encode(v: bytes) -> str:
    """ encode v, which is a string of bytes, to base58."""

    long_value = 0
    for c in v:
        long_value = long_value * 256 + c

    result = ""
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result

    # Bitcoin does a little leading-zero-compression:
    # leading 0-bytes in the input become leading-1s
    nPad = 0
    for c in v:
        if c == 0:
            nPad += 1
        else:
            break

    return (__b58chars[0] * nPad) + result


def b58decode(v: AnyStr, length: Optional[int] = None) -> bytes:
    """ decode v into a string of len bytes."""
    str_v = v.decode() if isinstance(v, bytes) else v

    for c in str_v:
        if c not in __b58chars:
            raise ValueError("invalid Base58 string")

    long_value = 0
    for (i, c) in enumerate(str_v[::-1]):
        long_value += __b58chars.find(c) * (__b58base ** i)

    result = b""
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = struct.pack("B", mod) + result
        long_value = div
    result = struct.pack("B", long_value) + result

    nPad = 0
    for c in str_v:
        if c == __b58chars[0]:
            nPad += 1
        else:
            break

    result = b"\x00" * nPad + result
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


def normalize_nfc(txt: AnyStr) -> bytes:
    """
    Normalize message to NFC and return bytes suitable for protobuf.
    This seems to be bitcoin-qt standard of doing things.
    """
    str_txt = txt.decode() if isinstance(txt, bytes) else txt
    return unicodedata.normalize("NFC", str_txt).encode()


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
