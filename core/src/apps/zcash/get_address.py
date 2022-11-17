from typing import TYPE_CHECKING

from trezor import wire
from trezor.crypto import base58
from trezor.crypto.scripts import sha256_ripemd160
from trezor.messages import ZcashAddress
from trezor.ui.layouts import show_address

from apps.bitcoin import keychain as t_keychain
from apps.common import address_type
from apps.common.coininfo import CoinInfo, by_name
from apps.common.paths import HARDENED, address_n_to_str

from .orchard import keychain as z_keychain
from .unified import Typecode, encode_address

if TYPE_CHECKING:
    from trezor.wire import Context
    from trezor.messages import ZcashGetAddress


def encode_p2pkh(raw_address: bytes, coin: CoinInfo) -> str:
    return base58.encode_check(address_type.tobytes(coin.address_type) + raw_address)


async def get_address(ctx: Context, msg: ZcashGetAddress) -> ZcashAddress:
    if not (msg.t_address_n or msg.z_address_n):
        raise wire.DataError("t-address or z-address path expected")

    coin = by_name(msg.coin_name)

    if msg.z_address_n:
        receivers = {}
        receivers[Typecode.ORCHARD] = await get_raw_orchard_address(ctx, msg)

        if msg.t_address_n:
            if msg.t_address_n[2] != msg.z_address_n[2]:
                raise wire.DataError("Receivers use different acount numbers.")
            receivers[Typecode.P2PKH] = await get_raw_transparent_address(
                ctx, coin, msg
            )

        title = "u/{coin_type}/{account}/{receivers}".format(
            coin_type=msg.z_address_n[1] ^ HARDENED,
            account=msg.z_address_n[2] ^ HARDENED,
            receivers=",".join(map(str, receivers.keys())),
        )

        address = encode_address(receivers, coin)

    else:  # has only t-address
        title = address_n_to_str(msg.t_address_n)
        raw_address = await get_raw_transparent_address(ctx, coin, msg)
        address = encode_p2pkh(raw_address, coin)

    if msg.show_display:
        await show_address(ctx, address=address, address_qr=address, title=title)

    return ZcashAddress(address=address)


async def get_raw_transparent_address(
    ctx: Context,
    coin: CoinInfo,
    msg: ZcashGetAddress,
) -> bytes:
    """Returns Zcash raw P2PKH transparent address."""
    keychain = await t_keychain.get_keychain_for_coin(ctx, coin)
    node = keychain.derive(msg.t_address_n)
    return sha256_ripemd160(node.public_key()).digest()


@z_keychain.with_keychain
async def get_raw_orchard_address(
    ctx: Context, msg: ZcashGetAddress, keychain: z_keychain.OrchardKeychain
) -> bytes:
    """Returns raw Zcash Orchard address."""
    fvk = keychain.derive(msg.z_address_n).full_viewing_key()
    return fvk.address(msg.diversifier_index).to_bytes()
