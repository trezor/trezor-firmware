from micropython import const

from trezor.crypto.hashlib import sha256, ripemd160
from trezor.crypto import base58, bech32, cashaddr
from trezor.utils import ensure

from trezor.messages import FailureType
from trezor.messages import InputScriptType

from apps.common.coininfo import CoinInfo
from apps.common.address_type import addrtype_bytes
from apps.wallet.sign_tx.scripts import *
from apps.wallet.sign_tx.multisig import *

# supported witness version for bech32 addresses
_BECH32_WITVER = const(0x00)


class AddressError(Exception):
    pass


def get_address(script_type: InputScriptType, coin: CoinInfo, node, multisig=None) -> str:

    if script_type == InputScriptType.SPENDADDRESS or script_type == InputScriptType.SPENDMULTISIG:
        if multisig:  # p2sh multisig
            pubkey = node.public_key()
            index = multisig_pubkey_index(multisig, pubkey)
            if index is None:
                raise AddressError(FailureType.ProcessError,
                                   'Public key not found')
            if coin.address_type_p2sh is None:
                raise AddressError(FailureType.ProcessError,
                                   'Multisig not enabled on this coin')

            pubkeys = multisig_get_pubkeys(multisig)
            address = address_multisig_p2sh(pubkeys, multisig.m, coin.address_type_p2sh)
            if coin.cashaddr_prefix is not None:
                address = address_to_cashaddr(address, coin)
            return address
        if script_type == InputScriptType.SPENDMULTISIG:
            raise AddressError(FailureType.ProcessError,
                               'Multisig details required')

        # p2pkh
        address = node.address(coin.address_type)
        if coin.cashaddr_prefix is not None:
            address = address_to_cashaddr(address, coin)
        return address

    elif script_type == InputScriptType.SPENDWITNESS:  # native p2wpkh or native p2wsh
        if not coin.segwit or not coin.bech32_prefix:
            raise AddressError(FailureType.ProcessError,
                               'Segwit not enabled on this coin')
        # native p2wsh multisig
        if multisig is not None:
            pubkeys = multisig_get_pubkeys(multisig)
            return address_multisig_p2wsh(pubkeys, multisig.m, coin.bech32_prefix)

        # native p2wpkh
        return address_p2wpkh(node.public_key(), coin.bech32_prefix)

    elif script_type == InputScriptType.SPENDP2SHWITNESS:  # p2wpkh or p2wsh nested in p2sh
        if not coin.segwit or coin.address_type_p2sh is None:
            raise AddressError(FailureType.ProcessError,
                               'Segwit not enabled on this coin')
        # p2wsh multisig nested in p2sh
        if multisig is not None:
            pubkeys = multisig_get_pubkeys(multisig)
            return address_multisig_p2wsh_in_p2sh(pubkeys, multisig.m, coin.address_type_p2sh)

        # p2wpkh nested in p2sh
        return address_p2wpkh_in_p2sh(node.public_key(), coin.address_type_p2sh)

    else:
        raise AddressError(FailureType.ProcessError,
                           'Invalid script type')


def address_multisig_p2sh(pubkeys: bytes, m: int, addrtype: int):
    if addrtype is None:
        raise AddressError(FailureType.ProcessError,
                           'Multisig not enabled on this coin')
    redeem_script = output_script_multisig(pubkeys, m)
    redeem_script_hash = sha256_ripemd160_digest(redeem_script)
    return address_p2sh(redeem_script_hash, addrtype)


def address_multisig_p2wsh_in_p2sh(pubkeys: bytes, m: int, addrtype: int):
    if addrtype is None:
        raise AddressError(FailureType.ProcessError,
                           'Multisig not enabled on this coin')
    witness_script = output_script_multisig(pubkeys, m)
    witness_script_hash = sha256(witness_script).digest()
    return address_p2wsh_in_p2sh(witness_script_hash, addrtype)


def address_multisig_p2wsh(pubkeys: bytes, m: int, hrp: str):
    if not hrp:
        raise AddressError(FailureType.ProcessError,
                           'Multisig not enabled on this coin')
    witness_script = output_script_multisig(pubkeys, m)
    witness_script_hash = sha256(witness_script).digest()
    return address_p2wsh(witness_script_hash, hrp)


def address_pkh(pubkey: bytes, addrtype: int) -> str:
    s = addrtype_bytes(addrtype) + sha256_ripemd160_digest(pubkey)
    return base58.encode_check(bytes(s))


def address_p2sh(redeem_script_hash: bytes, addrtype: int) -> str:
    s = addrtype_bytes(addrtype) + redeem_script_hash
    return base58.encode_check(bytes(s))


def address_p2wpkh_in_p2sh(pubkey: bytes, addrtype: int) -> str:
    pubkey_hash = ecdsa_hash_pubkey(pubkey)
    redeem_script = output_script_native_p2wpkh_or_p2wsh(pubkey_hash)
    redeem_script_hash = sha256_ripemd160_digest(redeem_script)
    return address_p2sh(redeem_script_hash, addrtype)


def address_p2wsh_in_p2sh(witness_script_hash: bytes, addrtype: int) -> str:
    redeem_script = output_script_native_p2wpkh_or_p2wsh(witness_script_hash)
    redeem_script_hash = sha256_ripemd160_digest(redeem_script)
    return address_p2sh(redeem_script_hash, addrtype)


def address_p2wpkh(pubkey: bytes, hrp: str) -> str:
    pubkeyhash = ecdsa_hash_pubkey(pubkey)
    address = bech32.encode(hrp, _BECH32_WITVER, pubkeyhash)
    if address is None:
        raise AddressError(FailureType.ProcessError,
                           'Invalid address')
    return address


def address_p2wsh(witness_script_hash: bytes, hrp: str) -> str:
    address = bech32.encode(hrp, _BECH32_WITVER, witness_script_hash)
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


def address_to_cashaddr(address: str, coin: CoinInfo) -> str:
    raw = base58.decode_check(address)
    version, data = raw[0], raw[1:]
    if version == coin.address_type:
        version = cashaddr.ADDRESS_TYPE_P2KH
    elif version == coin.address_type_p2sh:
        version = cashaddr.ADDRESS_TYPE_P2SH
    else:
        raise ValueError('Unknown cashaddr address type')
    return cashaddr.encode(coin.cashaddr_prefix, version, data)


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
