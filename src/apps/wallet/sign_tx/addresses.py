from micropython import const

from trezor.crypto.hashlib import sha256, ripemd160
from trezor.crypto import base58, bech32
from trezor.utils import ensure

from trezor.messages.CoinType import CoinType
from trezor.messages import FailureType
from trezor.messages import InputScriptType

# supported witness version for bech32 addresses
_BECH32_WITVER = const(0x00)


class AddressError(Exception):
    pass


def get_address(script_type: InputScriptType, coin: CoinType, node) -> str:

    if script_type == InputScriptType.SPENDADDRESS:  # p2pkh
        return node.address(coin.address_type)

    elif script_type == InputScriptType.SPENDWITNESS:  # native p2wpkh
        if not coin.segwit or not coin.bech32_prefix:
            raise AddressError(FailureType.ProcessError,
                               'Segwit not enabled on this coin')
        return address_p2wpkh(node.public_key(), coin.bech32_prefix)

    elif script_type == InputScriptType.SPENDP2SHWITNESS:  # p2wpkh using p2sh
        if not coin.segwit or not coin.address_type_p2sh:
            raise AddressError(FailureType.ProcessError,
                               'Segwit not enabled on this coin')
        return address_p2wpkh_in_p2sh(node.public_key(), coin.address_type_p2sh)

    else:
        raise AddressError(FailureType.ProcessError,
                           'Invalid script type')


def address_p2wpkh_in_p2sh(pubkey: bytes, addrtype: int) -> str:
    s = bytearray(21)
    s[0] = addrtype
    s[1:21] = address_p2wpkh_in_p2sh_raw(pubkey)
    return base58.encode_check(bytes(s))


def address_p2wpkh_in_p2sh_raw(pubkey: bytes) -> bytes:
    s = bytearray(22)
    s[0] = 0x00  # OP_0
    s[1] = 0x14  # pushing 20 bytes
    s[2:22] = ecdsa_hash_pubkey(pubkey)
    h = sha256(s).digest()
    h = ripemd160(h).digest()
    return h


def address_p2wpkh(pubkey: bytes, hrp: str) -> str:
    pubkeyhash = ecdsa_hash_pubkey(pubkey)
    address = bech32.encode(hrp, _BECH32_WITVER, pubkeyhash)
    if address is None:
        raise AddressError(FailureType.ProcessError,
                           'Invalid address')
    return address


def decode_bech32_address(prefix: str, address: str) -> bytes:
    witver, raw = bech32.decode(prefix, address)
    if witver != _BECH32_WITVER:
        raise AddressError(FailureType.ProcessError,
                           'Invalid address witness program')
    return bytes(raw)


def ecdsa_hash_pubkey(pubkey: bytes) -> bytes:
    if pubkey[0] == 0x04:
        ensure(len(pubkey) == 65)  # uncompressed format
    elif pubkey[0] == 0x00:
        ensure(len(pubkey) == 1)   # point at infinity
    else:
        ensure(len(pubkey) == 33)  # compresssed format
    h = sha256(pubkey).digest()
    h = ripemd160(h).digest()
    return h
