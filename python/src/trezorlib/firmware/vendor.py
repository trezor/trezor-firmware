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

import hashlib
import typing as t
from copy import copy

import construct as c
from construct_classes import Struct, subcon

from .. import cosi
from ..toif import ToifStruct
from ..tools import EnumAdapter, TupleAdapter
from . import util
from .models import Model

__all__ = [
    "VendorTrust",
    "VendorHeader",
]


def _transform_vendor_trust(data: bytes) -> bytes:
    """Byte-swap and bit-invert the VendorTrust field.

    Vendor trust is interpreted as a bitmask in a 16-bit little-endian integer,
    with the added twist that 0 means set and 1 means unset.
    We feed it to a `BitStruct` that expects a big-endian sequence where bits have
    the traditional meaning. We must therefore do a bitwise negation of each byte,
    and return them in reverse order. This is the same transformation both ways,
    fortunately, so we don't need two separate functions.
    """
    return bytes(~b & 0xFF for b in data)[::-1]


class VendorTrust(Struct):
    allow_run_with_secret: bool
    show_vendor_string: bool
    require_user_click: bool
    red_background: bool
    delay: int

    _reserved: int = 0

    SUBCON = c.Transformed(
        c.BitStruct(
            "_reserved" / c.Default(c.BitsInteger(8), 0),
            "allow_run_with_secret" / c.Flag,
            "show_vendor_string" / c.Flag,
            "require_user_click" / c.Flag,
            "red_background" / c.Flag,
            "delay" / c.BitsInteger(4),
        ),
        _transform_vendor_trust,
        2,
        _transform_vendor_trust,
        2,
    )

    def is_full_trust(self) -> bool:
        return (
            not self.show_vendor_string
            and not self.require_user_click
            and not self.red_background
            and self.delay == 0
        )


class VendorHeader(Struct):
    header_len: int
    expiry: int
    version: t.Tuple[int, int]
    sig_m: int
    # sig_n: int
    hw_model: t.Union[Model, bytes]
    pubkeys: t.List[bytes]
    text: str
    image: t.Dict[str, t.Any]
    sigmask: int
    signature: bytes

    trust: VendorTrust = subcon(VendorTrust)

    # fmt: off
    SUBCON = c.Struct(
        "_start_offset" / c.Tell,
        "magic" / c.Const(b"TRZV"),
        "header_len" / c.Int32ul,
        "expiry" / c.Int32ul,
        "version" / TupleAdapter(c.Int8ul, c.Int8ul),
        "sig_m" / c.Int8ul,
        "sig_n" / c.Rebuild(c.Int8ul, c.len_(c.this.pubkeys)),
        "trust" / VendorTrust.SUBCON,
        "hw_model" / EnumAdapter(c.Bytes(4), Model),
        "_reserved" / c.Padding(10),
        "pubkeys" / c.Bytes(32)[c.this.sig_n],
        "text" / c.Aligned(4, c.PascalString(c.Int8ul, "utf-8")),
        "image" / ToifStruct,
        "_end_offset" / c.Tell,

        "_min_header_len" / c.Check(c.this.header_len > (c.this._end_offset - c.this._start_offset) + 65),
        "_header_len_aligned" / c.Check(c.this.header_len % 512 == 0),

        c.Padding(c.this.header_len - c.this._end_offset + c.this._start_offset - 65),
        "sigmask" / c.Byte,
        "signature" / c.Bytes(64),
    )
    # fmt: on

    def digest(self) -> bytes:
        cpy = copy(self)
        cpy.sigmask = 0
        cpy.signature = b"\x00" * 64
        return hashlib.blake2s(cpy.build()).digest()

    def vhash(self) -> bytes:
        h = hashlib.blake2s()
        sig_n = len(self.pubkeys)
        h.update(self.sig_m.to_bytes(1, "little"))
        h.update(sig_n.to_bytes(1, "little"))
        for i in range(8):
            if i < sig_n:
                h.update(self.pubkeys[i])
            else:
                h.update(b"\x00" * 32)
        return h.digest()

    def verify(self, dev_keys: bool = False) -> None:
        digest = self.digest()
        model_keys = Model.from_hw_model(self.hw_model).model_keys(dev_keys)
        try:
            cosi.verify(
                self.signature,
                digest,
                model_keys.bootloader_sigs_needed,
                model_keys.bootloader_keys,
                self.sigmask,
            )
        except Exception:
            raise util.InvalidSignatureError("Invalid vendor header signature.")

        # XXX expiry is not used now
        # now = time.gmtime()
        # if time.gmtime(fw.vendor_header.expiry) < now:
        #     raise ValueError("Vendor header expired.")
