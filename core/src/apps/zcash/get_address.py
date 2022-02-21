from trezor.messages import ZcashGetAddress, ZcashAddress
from trezor.ui.layouts import show_address

from apps import bitcoin
from apps.common.paths import address_n_to_str, HARDENED
from apps.common.coininfo import CoinInfo

from trezor.crypto.scripts import sha256_ripemd160
from trezor import log, wire

from . import orchard
from .address import (
    encode_unified, encode_transparent,
    P2PKH, MAINNET, TESTNET, ORCHARD, P2PKH
)

if False:
    from trezor.wire import Context

async def get_address(ctx: Context, msg: ZcashGetAddress) -> ZcashAddress:
    has_t_addr = len(msg.t_address_n) != 0
    has_z_addr = len(msg.z_address_n) != 0

    if not (has_t_addr or has_z_addr):
        raise wire.DataError("t-address or z-address expected")

    network = {
        "Zcash": MAINNET,
        "Zcash Testnet": TESTNET,
    }[msg.coin_name]

    if has_z_addr:
        receivers = dict()
        receivers[ORCHARD] = await get_raw_orchard_address(ctx, msg)

        if has_t_addr:
            if msg.t_address_n[2] != msg.z_address_n[2]:
                raise wire.DataError("Receivers use different acount numbers.")

            receivers[P2PKH] = await get_raw_transparent_address(ctx, msg)
        title = "u/{coin_type}/{account}/{receivers}".format(
            coin_type   = msg.z_address_n[1] ^ HARDENED,
            account     = msg.z_address_n[2] ^ HARDENED,
            receivers   = ",".join(map(str, receivers.keys())),
            #diversifier = msg.diversifier_index,
        )

        address = encode_unified(receivers, network)

    else:  # has only t-address
        title = address_n_to_str(msg.t_address_n)
        raw_address = await get_raw_transparent_address(ctx, msg)
        address = encode_transparent(raw_address, network)

    if msg.show_display:
        await show_address(
            ctx, address=address, address_qr=address, title=title
        )

    return ZcashAddress(address=address)


@bitcoin.keychain.with_keychain
async def get_raw_transparent_address(
    ctx: Context,
    msg: GetZcashAddress,
    keychain: bitcoin.keychain.Keychain,
    coin: CoinInfo,
    auth_msg: MessageType | None = None
) -> bytes:
    """Returns Zcash raw P2PKH transparent address."""
    node = keychain.derive(msg.t_address_n)
    return sha256_ripemd160(node.public_key()).digest()


@orchard.keychain.with_keychain
async def get_raw_orchard_address(
    ctx: Context,
    msg: GetZcashAddress,
    keychain: orchard.keychain.OrchardKeychain
) -> bytes:
    """Returns raw Zcash Orchard address."""
    return keychain.derive(msg.z_address_n).address(msg.diversifier_index)
