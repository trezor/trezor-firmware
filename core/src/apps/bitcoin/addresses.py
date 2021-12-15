from trezor import wire
from trezor.crypto import base58, cashaddr
from trezor.crypto.curve import bip340
from trezor.crypto.hashlib import sha256
from trezor.enums import InputScriptType
from trezor.messages import MultisigRedeemScriptType
from trezor.utils import HashWriter

from apps.common import address_type
from apps.common.coininfo import CoinInfo

from .common import ecdsa_hash_pubkey, encode_bech32_address
from .multisig import multisig_get_pubkeys, multisig_pubkey_index
from .scripts import output_script_native_segwit, write_output_script_multisig

if False:
    from trezor.crypto import bip32


def get_address(
    script_type: InputScriptType,
    coin: CoinInfo,
    node: bip32.HDNode,
    multisig: MultisigRedeemScriptType | None = None,
) -> str:
    if multisig:
        # Ensure that our public key is included in the multisig.
        multisig_pubkey_index(multisig, node.public_key())

    if script_type in (InputScriptType.SPENDADDRESS, InputScriptType.SPENDMULTISIG):
        if multisig:  # p2sh multisig
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

    elif script_type == InputScriptType.SPENDTAPROOT:  # taproot
        if not coin.taproot or not coin.bech32_prefix:
            raise wire.ProcessError("Taproot not enabled on this coin")

        if multisig is not None:
            raise wire.ProcessError("Multisig not supported for taproot")

        return address_p2tr(node.public_key(), coin)

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


def address_multisig_p2sh(pubkeys: list[bytes], m: int, coin: CoinInfo) -> str:
    if coin.address_type_p2sh is None:
        raise wire.ProcessError("Multisig not enabled on this coin")
    redeem_script = HashWriter(coin.script_hash())
    write_output_script_multisig(redeem_script, pubkeys, m)
    return address_p2sh(redeem_script.get_digest(), coin)


def address_multisig_p2wsh_in_p2sh(pubkeys: list[bytes], m: int, coin: CoinInfo) -> str:
    if coin.address_type_p2sh is None:
        raise wire.ProcessError("Multisig not enabled on this coin")
    witness_script_h = HashWriter(sha256())
    write_output_script_multisig(witness_script_h, pubkeys, m)
    return address_p2wsh_in_p2sh(witness_script_h.get_digest(), coin)


def address_multisig_p2wsh(pubkeys: list[bytes], m: int, hrp: str) -> str:
    if not hrp:
        raise wire.ProcessError("Multisig not enabled on this coin")
    witness_script_h = HashWriter(sha256())
    write_output_script_multisig(witness_script_h, pubkeys, m)
    return address_p2wsh(witness_script_h.get_digest(), hrp)


def address_pkh(pubkey: bytes, coin: CoinInfo) -> str:
    s = address_type.tobytes(coin.address_type) + coin.script_hash(pubkey).digest()
    return base58.encode_check(bytes(s), coin.b58_hash)


def address_p2sh(redeem_script_hash: bytes, coin: CoinInfo) -> str:
    s = address_type.tobytes(coin.address_type_p2sh) + redeem_script_hash
    return base58.encode_check(bytes(s), coin.b58_hash)


def address_p2wpkh_in_p2sh(pubkey: bytes, coin: CoinInfo) -> str:
    pubkey_hash = ecdsa_hash_pubkey(pubkey, coin)
    redeem_script = output_script_native_segwit(0, pubkey_hash)
    redeem_script_hash = coin.script_hash(redeem_script).digest()
    return address_p2sh(redeem_script_hash, coin)


def address_p2wsh_in_p2sh(witness_script_hash: bytes, coin: CoinInfo) -> str:
    redeem_script = output_script_native_segwit(0, witness_script_hash)
    redeem_script_hash = coin.script_hash(redeem_script).digest()
    return address_p2sh(redeem_script_hash, coin)


def address_p2wpkh(pubkey: bytes, coin: CoinInfo) -> str:
    assert coin.bech32_prefix is not None
    pubkeyhash = ecdsa_hash_pubkey(pubkey, coin)
    return encode_bech32_address(coin.bech32_prefix, 0, pubkeyhash)


def address_p2wsh(witness_script_hash: bytes, hrp: str) -> str:
    return encode_bech32_address(hrp, 0, witness_script_hash)


def address_p2tr(pubkey: bytes, coin: CoinInfo) -> str:
    assert coin.bech32_prefix is not None
    output_pubkey = bip340.tweak_public_key(pubkey[1:])
    return encode_bech32_address(coin.bech32_prefix, 1, output_pubkey)


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
