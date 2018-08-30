from micropython import const

from trezor.crypto import base58, bech32, cashaddr
from trezor.crypto.hashlib import sha256
from trezor.messages import FailureType, InputScriptType
from trezor.utils import ensure

from apps.common import HARDENED, address_type, paths
from apps.common.coininfo import CoinInfo
from apps.wallet.sign_tx.multisig import multisig_get_pubkeys, multisig_pubkey_index
from apps.wallet.sign_tx.scripts import (
    output_script_multisig,
    output_script_native_p2wpkh_or_p2wsh,
)

# supported witness version for bech32 addresses
_BECH32_WITVER = const(0x00)


class AddressError(Exception):
    pass


def get_address(
    script_type: InputScriptType, coin: CoinInfo, node, multisig=None
) -> str:

    if (
        script_type == InputScriptType.SPENDADDRESS
        or script_type == InputScriptType.SPENDMULTISIG
    ):
        if multisig:  # p2sh multisig
            pubkey = node.public_key()
            index = multisig_pubkey_index(multisig, pubkey)
            if index is None:
                raise AddressError(FailureType.ProcessError, "Public key not found")
            if coin.address_type_p2sh is None:
                raise AddressError(
                    FailureType.ProcessError, "Multisig not enabled on this coin"
                )

            pubkeys = multisig_get_pubkeys(multisig)
            address = address_multisig_p2sh(pubkeys, multisig.m, coin)
            if coin.cashaddr_prefix is not None:
                address = address_to_cashaddr(address, coin)
            return address
        if script_type == InputScriptType.SPENDMULTISIG:
            raise AddressError(FailureType.ProcessError, "Multisig details required")

        # p2pkh
        address = node.address(coin.address_type)
        if coin.cashaddr_prefix is not None:
            address = address_to_cashaddr(address, coin)
        return address

    elif script_type == InputScriptType.SPENDWITNESS:  # native p2wpkh or native p2wsh
        if not coin.segwit or not coin.bech32_prefix:
            raise AddressError(
                FailureType.ProcessError, "Segwit not enabled on this coin"
            )
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
            raise AddressError(
                FailureType.ProcessError, "Segwit not enabled on this coin"
            )
        # p2wsh multisig nested in p2sh
        if multisig is not None:
            pubkeys = multisig_get_pubkeys(multisig)
            return address_multisig_p2wsh_in_p2sh(pubkeys, multisig.m, coin)

        # p2wpkh nested in p2sh
        return address_p2wpkh_in_p2sh(node.public_key(), coin)

    else:
        raise AddressError(FailureType.ProcessError, "Invalid script type")


def address_multisig_p2sh(pubkeys: bytes, m: int, coin: CoinInfo):
    if coin.address_type_p2sh is None:
        raise AddressError(
            FailureType.ProcessError, "Multisig not enabled on this coin"
        )
    redeem_script = output_script_multisig(pubkeys, m)
    redeem_script_hash = coin.script_hash(redeem_script)
    return address_p2sh(redeem_script_hash, coin)


def address_multisig_p2wsh_in_p2sh(pubkeys: bytes, m: int, coin: CoinInfo):
    if coin.address_type_p2sh is None:
        raise AddressError(
            FailureType.ProcessError, "Multisig not enabled on this coin"
        )
    witness_script = output_script_multisig(pubkeys, m)
    witness_script_hash = sha256(witness_script).digest()
    return address_p2wsh_in_p2sh(witness_script_hash, coin)


def address_multisig_p2wsh(pubkeys: bytes, m: int, hrp: str):
    if not hrp:
        raise AddressError(
            FailureType.ProcessError, "Multisig not enabled on this coin"
        )
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
    pubkeyhash = ecdsa_hash_pubkey(pubkey, coin)
    address = bech32.encode(coin.bech32_prefix, _BECH32_WITVER, pubkeyhash)
    if address is None:
        raise AddressError(FailureType.ProcessError, "Invalid address")
    return address


def address_p2wsh(witness_script_hash: bytes, hrp: str) -> str:
    address = bech32.encode(hrp, _BECH32_WITVER, witness_script_hash)
    if address is None:
        raise AddressError(FailureType.ProcessError, "Invalid address")
    return address


def decode_bech32_address(prefix: str, address: str) -> bytes:
    witver, raw = bech32.decode(prefix, address)
    if witver != _BECH32_WITVER:
        raise AddressError(FailureType.ProcessError, "Invalid address witness program")
    return bytes(raw)


def address_to_cashaddr(address: str, coin: CoinInfo) -> str:
    raw = base58.decode_check(address, coin.b58_hash)
    version, data = raw[0], raw[1:]
    if version == coin.address_type:
        version = cashaddr.ADDRESS_TYPE_P2KH
    elif version == coin.address_type_p2sh:
        version = cashaddr.ADDRESS_TYPE_P2SH
    else:
        raise ValueError("Unknown cashaddr address type")
    return cashaddr.encode(coin.cashaddr_prefix, version, data)


def ecdsa_hash_pubkey(pubkey: bytes, coin: CoinInfo) -> bytes:
    if pubkey[0] == 0x04:
        ensure(len(pubkey) == 65)  # uncompressed format
    elif pubkey[0] == 0x00:
        ensure(len(pubkey) == 1)  # point at infinity
    else:
        ensure(len(pubkey) == 33)  # compresssed format

    return coin.script_hash(pubkey)


def address_short(coin: CoinInfo, address: str) -> str:
    if coin.cashaddr_prefix is not None and address.startswith(
        coin.cashaddr_prefix + ":"
    ):
        return address[len(coin.cashaddr_prefix) + 1 :]
    else:
        return address


def validate_full_path(
    path: list, coin: CoinInfo, script_type: InputScriptType
) -> bool:
    """
    Validates derivation path to fit Bitcoin-like coins. We mostly use
    44', but for segwit-enabled coins we use either 49' (P2WPKH-nested-in-P2SH)
    or 84' (native P2WPKH). Electrum uses m/45' for legacy addresses and
    m/48' for segwit, so those two are allowed as well.

    See docs/coins for what paths are allowed. Please note that this is not
    a comprehensive check, some nuances are omitted for simplification.
    """
    if len(path) != 5:
        return False

    if not validate_purpose(path[0], coin):
        return False
    if not validate_purpose_against_script_type(path[0], script_type):
        return False

    if path[1] != coin.slip44 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 20 | HARDENED:
        return False
    if path[3] not in [0, 1]:
        return False
    if path[4] > 1000000:
        return False
    return True


def validate_purpose(purpose: int, coin: CoinInfo) -> bool:
    if purpose not in (44 | HARDENED, 48 | HARDENED, 49 | HARDENED, 84 | HARDENED):
        return False
    if not coin.segwit and purpose not in (44 | HARDENED, 48 | HARDENED):
        return False
    return True


def validate_purpose_against_script_type(
    purpose: int, script_type: InputScriptType
) -> bool:
    """
    Validates purpose against provided input's script type:
    - 44 for spending address (script_type == SPENDADDRESS)
    - 48 for multisig (script_type == SPENDMULTISIG)
    - 49 for p2sh-segwit spend (script_type == SPENDP2SHWITNESS)
    - 84 for native segwit spend (script_type == SPENDWITNESS)
    """
    if purpose == 44 | HARDENED and script_type != InputScriptType.SPENDADDRESS:
        return False
    if purpose == 48 | HARDENED and script_type != InputScriptType.SPENDMULTISIG:
        return False
    if (  # p2wsh-nested-in-p2sh
        purpose == 49 | HARDENED and script_type != InputScriptType.SPENDP2SHWITNESS
    ):
        return False
    if (  # p2wsh
        purpose == 84 | HARDENED and script_type != InputScriptType.SPENDWITNESS
    ):
        return False
    return True


def validate_path_for_bitcoin_public_key(path: list, coin: CoinInfo) -> bool:
    """
    Validates derivation path to fit Bitcoin-like coins for GetPublicKey.
    Script type is omitted here because it is not usually sent.
    """
    length = len(path)
    if length < 3 or length > 5:
        return False

    if not validate_purpose(path[0], coin):
        return False

    if path[1] != coin.slip44 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 20 | HARDENED:
        return False
    if length > 3 and paths.is_hardened(path[3]):
        return False
    if length > 4 and paths.is_hardened(path[4]):
        return False
    return True
