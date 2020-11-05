from trezor import wire
from trezor.crypto import base58, cashaddr
from trezor.crypto.hashlib import sha256
from trezor.messages import InputScriptType
from trezor.messages.MultisigRedeemScriptType import MultisigRedeemScriptType

from apps.common import address_type
from apps.common.coininfo import CoinInfo

from .common import ecdsa_hash_pubkey, encode_bech32_address
from .multisig import multisig_get_pubkeys, multisig_pubkey_index
from .scripts import output_script_multisig, output_script_native_p2wpkh_or_p2wsh

if False:
    from typing import List
    from trezor.crypto import bip32
    from trezor.messages.TxInputType import EnumTypeInputScriptType


def get_address(
    script_type: EnumTypeInputScriptType,
    coin: CoinInfo,
    node: bip32.HDNode,
    multisig: MultisigRedeemScriptType = None,
) -> str:

    if (
        script_type == InputScriptType.SPENDADDRESS
        or script_type == InputScriptType.SPENDMULTISIG
    ):
        if multisig:  # p2sh multisig
            pubkey = node.public_key()
            index = multisig_pubkey_index(multisig, pubkey)
            if index is None:
                raise wire.ProcessError("Public key not found")
            if coin.address_type_p2sh is None:
                raise wire.ProcessError("Multisig not enabled on this coin")

            pubkeys = multisig_get_pubkeys(multisig)
            address = address_multisig_p2sh(pubkeys, multisig.m, coin)
            if coin.cashaddr_prefix is not None:
                address = address_to_cashaddr(address, coin)
            return address
        if script_type == InputScriptType.SPENDMULTISIG:
            raise wire.ProcessError("Multisig details required")

        # p2pkh
        address = node.address(coin.address_type)
        if coin.cashaddr_prefix is not None:
            address = address_to_cashaddr(address, coin)
        return address

    elif script_type == InputScriptType.SPENDWITNESS:  # native p2wpkh or native p2wsh
        if not coin.segwit or not coin.bech32_prefix:
            raise wire.ProcessError("Segwit not enabled on this coin")
        # native p2wsh multisig
        if multisig is not None:
            pubkeys = multisig_get_pubkeys(multisig)
            return address_multisig_p2wsh(pubkeys, multisig.m, coin.bech32_prefix)

        # native p2wpkh
        return address_p2wpkh(node.public_key(), coin)

    elif (
        script_type == InputScriptType.SPENDP2SHWITNESS
    ):  # p2wpkh or p2wsh nested in p2sh
        if not coin.segwit or coin.address_type_p2sh is None:
            raise wire.ProcessError("Segwit not enabled on this coin")
        # p2wsh multisig nested in p2sh
        if multisig is not None:
            pubkeys = multisig_get_pubkeys(multisig)
            return address_multisig_p2wsh_in_p2sh(pubkeys, multisig.m, coin)

        # p2wpkh nested in p2sh
        return address_p2wpkh_in_p2sh(node.public_key(), coin)

    else:
        raise wire.ProcessError("Invalid script type")


def address_multisig_p2sh(pubkeys: List[bytes], m: int, coin: CoinInfo) -> str:
    if coin.address_type_p2sh is None:
        raise wire.ProcessError("Multisig not enabled on this coin")
    redeem_script = output_script_multisig(pubkeys, m)
    redeem_script_hash = coin.script_hash(redeem_script)
    return address_p2sh(redeem_script_hash, coin)


def address_multisig_p2wsh_in_p2sh(pubkeys: List[bytes], m: int, coin: CoinInfo) -> str:
    if coin.address_type_p2sh is None:
        raise wire.ProcessError("Multisig not enabled on this coin")
    witness_script = output_script_multisig(pubkeys, m)
    witness_script_hash = sha256(witness_script).digest()
    return address_p2wsh_in_p2sh(witness_script_hash, coin)


def address_multisig_p2wsh(pubkeys: List[bytes], m: int, hrp: str) -> str:
    if not hrp:
        raise wire.ProcessError("Multisig not enabled on this coin")
    witness_script = output_script_multisig(pubkeys, m)
    witness_script_hash = sha256(witness_script).digest()
    return address_p2wsh(witness_script_hash, hrp)


def address_pkh(pubkey: bytes, coin: CoinInfo) -> str:
    s = address_type.tobytes(coin.address_type) + coin.script_hash(pubkey)
    return base58.encode_check(bytes(s), coin.b58_hash)


def address_p2sh(redeem_script_hash: bytes, coin: CoinInfo) -> str:
    s = address_type.tobytes(coin.address_type_p2sh) + redeem_script_hash
    return base58.encode_check(bytes(s), coin.b58_hash)


def address_p2wpkh_in_p2sh(pubkey: bytes, coin: CoinInfo) -> str:
    pubkey_hash = ecdsa_hash_pubkey(pubkey, coin)
    redeem_script = output_script_native_p2wpkh_or_p2wsh(pubkey_hash)
    redeem_script_hash = coin.script_hash(redeem_script)
    return address_p2sh(redeem_script_hash, coin)


def address_p2wsh_in_p2sh(witness_script_hash: bytes, coin: CoinInfo) -> str:
    redeem_script = output_script_native_p2wpkh_or_p2wsh(witness_script_hash)
    redeem_script_hash = coin.script_hash(redeem_script)
    return address_p2sh(redeem_script_hash, coin)


def address_p2wpkh(pubkey: bytes, coin: CoinInfo) -> str:
    assert coin.bech32_prefix is not None
    pubkeyhash = ecdsa_hash_pubkey(pubkey, coin)
    return encode_bech32_address(coin.bech32_prefix, pubkeyhash)


def address_p2wsh(witness_script_hash: bytes, hrp: str) -> str:
    return encode_bech32_address(hrp, witness_script_hash)


def address_to_cashaddr(address: str, coin: CoinInfo) -> str:
    assert coin.cashaddr_prefix is not None
    raw = base58.decode_check(address, coin.b58_hash)
    version, data = raw[0], raw[1:]
    if version == coin.address_type:
        version = cashaddr.ADDRESS_TYPE_P2KH
    elif version == coin.address_type_p2sh:
        version = cashaddr.ADDRESS_TYPE_P2SH
    else:
        raise ValueError("Unknown cashaddr address type")
    return cashaddr.encode(coin.cashaddr_prefix, version, data)


def address_short(coin: CoinInfo, address: str) -> str:
    if coin.cashaddr_prefix is not None and address.startswith(
        coin.cashaddr_prefix + ":"
    ):
        return address[len(coin.cashaddr_prefix) + 1 :]
    else:
        return address
