# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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
import hmac
import struct
from copy import copy
from typing import Any, List, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers

from trezorlib import messages, tools

# secp256k1 curve parameters
_SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def _point_add(x1, y1, x2, y2):
    """Add two points on secp256k1. Returns (None, None) for point at infinity."""
    p = _SECP256K1_P
    if x1 is None:
        return (x2, y2)
    if x2 is None:
        return (x1, y1)
    if x1 == x2:
        if y1 != y2:
            return (None, None)
        lam = (3 * x1 * x1) * pow(2 * y1, -1, p) % p
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (lam * lam - x1 - x2) % p
    y3 = (lam * (x1 - x3) - y1) % p
    return (x3, y3)


def point_to_pubkey(x: int, y: int) -> bytes:
    nums = EllipticCurvePublicNumbers(x, y, ec.SECP256K1())
    key = nums.public_key()
    return key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.CompressedPoint
    )


def sec_to_public_pair(pubkey: bytes) -> Tuple[int, int]:
    """Convert a public key in sec binary format to a public pair."""
    sec0 = pubkey[:1]
    if sec0 not in (b"\2", b"\3"):
        raise ValueError("Compressed pubkey expected")

    key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pubkey)
    nums = key.public_numbers()
    return (nums.x, nums.y)


def fingerprint(pubkey: bytes) -> int:
    return int.from_bytes(tools.hash_160(pubkey)[:4], "big")


def get_address(public_node: messages.HDNodeType, address_type: int) -> str:
    return tools.public_key_to_bc_address(public_node.public_key, address_type)


def public_ckd(public_node: messages.HDNodeType, n: List[int]):
    if not isinstance(n, list):
        raise ValueError("Parameter must be a list")

    node = copy(public_node)

    for i in n:
        node = get_subnode(node, i)

    return node


def get_subnode(node: messages.HDNodeType, i: int) -> messages.HDNodeType:
    # Public Child key derivation (CKD) algorithm of BIP32
    i_as_bytes = struct.pack(">L", i)

    if i & tools.HARDENED_FLAG:
        raise ValueError("Prime derivation not supported")

    # Public derivation
    data = node.public_key + i_as_bytes

    I64 = hmac.HMAC(key=node.chain_code, msg=data, digestmod=hashlib.sha512).digest()
    I_left_as_exponent = int.from_bytes(I64[:32], "big")

    # BIP32 magic converts old public key to new public point
    x, y = sec_to_public_pair(node.public_key)

    # Compute I_left * G using cryptography
    il_key = ec.derive_private_key(I_left_as_exponent, ec.SECP256K1())
    il_pub = il_key.public_key().public_numbers()

    # Add I_left * G + parent public key point
    rx, ry = _point_add(il_pub.x, il_pub.y, x, y)

    if rx is None:
        raise ValueError("Point cannot be INFINITY")

    return messages.HDNodeType(
        depth=node.depth + 1,
        child_num=i,
        chain_code=I64[32:],
        fingerprint=fingerprint(node.public_key),
        # Convert public point to compressed public key
        public_key=point_to_pubkey(rx, ry),
    )


def serialize(node: messages.HDNodeType, version: int = 0x0488B21E) -> str:
    s = b""
    s += struct.pack(">I", version)
    s += struct.pack(">B", node.depth)
    s += struct.pack(">I", node.fingerprint)
    s += struct.pack(">I", node.child_num)
    s += node.chain_code
    if node.private_key:
        s += b"\x00" + node.private_key
    else:
        s += node.public_key
    s += tools.btc_hash(s)[:4]
    return tools.b58encode(s)


def deserialize(xpub: str) -> messages.HDNodeType:
    data = tools.b58decode(xpub, None)

    if tools.btc_hash(data[:-4])[:4] != data[-4:]:
        raise ValueError("Checksum failed")

    node = messages.HDNodeType(
        depth=struct.unpack(">B", data[4:5])[0],
        fingerprint=struct.unpack(">I", data[5:9])[0],
        child_num=struct.unpack(">I", data[9:13])[0],
        chain_code=data[13:45],
        public_key=None,
    )

    key = data[45:-4]
    if key[0] == 0:
        node.private_key = key[1:]
    else:
        node.public_key = key

    return node
