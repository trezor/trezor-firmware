from typing import TYPE_CHECKING

from trezor import wire
from trezor.crypto import base58
from trezor.crypto.scripts import sha256_ripemd160
from trezor.messages import ZcashAddress
from trezor.ui.layouts import show_address

from apps.bitcoin import keychain as t_keychain
from apps.common import address_type
from apps.common.coininfo import CoinInfo, by_name
from apps.common.paths import (
    HARDENED,
    PATTERN_BIP44,
    PathSchema,
    address_n_to_str,
    validate_path,
)

from .orchard.keychain import PATTERN_ZIP32, OrchardKeychain
from .unified import Typecode, encode_address

if TYPE_CHECKING:
    from trezor.wire import Context
    from trezor.messages import ZcashGetAddress


ORCHARD = Typecode.ORCHARD
P2PKH = Typecode.P2PKH


def encode_p2pkh(raw_address: bytes, coin: CoinInfo) -> str:
    return base58.encode_check(address_type.tobytes(coin.address_type) + raw_address)


async def get_address(ctx: Context, msg: ZcashGetAddress) -> ZcashAddress:
    coin = by_name(msg.coin_name)
    address_extra = None
    receivers = {}
    if msg.z_address_n:
        receivers[ORCHARD] = await get_raw_orchard_address(ctx, coin, msg)
    if msg.t_address_n:
        receivers[P2PKH] = await get_raw_transparent_address(ctx, coin, msg)

    if tuple(receivers.keys()) == ():  # no receivers
        raise wire.DataError("t-address or z-address path expected")
    elif tuple(receivers.keys()) == (P2PKH,):  # only transparent receiver
        title = address_n_to_str(msg.t_address_n)
        address = encode_p2pkh(receivers[P2PKH], coin)
    elif tuple(receivers.keys()) == (ORCHARD,):  # only shielded receiver
        title = address_n_to_str(msg.z_address_n)
        address = encode_address(receivers, coin)
    elif (  # transparent + shielded, unified path
        msg.t_address_n[2] == msg.z_address_n[2]  # spending from same account
        and PathSchema.parse(PATTERN_BIP44, coin.slip44).match(msg.t_address_n)
        and PathSchema.parse(PATTERN_ZIP32, coin.slip44).match(msg.z_address_n)
    ):
        title = "u/{coin_type}/{account}/{receivers}".format(
            coin_type=msg.z_address_n[1] ^ HARDENED,
            account=msg.z_address_n[2] ^ HARDENED,
            receivers=",".join(map(str, receivers.keys())),
        )
        address = encode_address(receivers, coin)
    else:  # transparent + shielded, incompatible paths
        title = "Unified address"
        address_extra = "\n".join(
            (
                "Receivers:",
                "- transparent",
                address_n_to_str(msg.t_address_n),
                "- Orchard",
                address_n_to_str(msg.z_address_n),
            )
        )
        address = encode_address(receivers, coin)

    if msg.show_display:
        await show_address(
            ctx,
            address=address,
            address_qr=address,
            title=title,
            address_extra=address_extra,
        )

    return ZcashAddress(address=address)


async def get_raw_transparent_address(
    ctx: Context,
    coin: CoinInfo,
    msg: ZcashGetAddress,
) -> bytes:
    """Returns Zcash raw P2PKH transparent address."""
    keychain = await t_keychain.get_keychain_for_coin(ctx, coin)
    if msg.show_display:
        await validate_path(ctx, keychain, msg.t_address_n)
    node = keychain.derive(msg.t_address_n)
    return sha256_ripemd160(node.public_key()).digest()


async def get_raw_orchard_address(
    ctx: Context, coin: CoinInfo, msg: ZcashGetAddress
) -> bytes:
    """Returns raw Zcash Orchard address."""
    keychain = await OrchardKeychain.for_coin(ctx, coin)
    if msg.show_display:
        await validate_path(ctx, keychain, msg.z_address_n)
    fvk = keychain.derive(msg.z_address_n).full_viewing_key()
    return fvk.address(msg.diversifier_index).to_bytes()
