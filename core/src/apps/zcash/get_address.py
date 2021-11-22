from trezor.messages import ZcashGetAddress, ZcashAddress
from trezor.ui.layouts import show_address

from apps.common.keychain import get_keychain
from apps.common.paths import address_n_to_str,\
                              PATTERN_BIP44, PathSchema, HARDENED

from trezor.crypto import zcash
from trezor.crypto.scripts import sha256_ripemd160
from trezor import log, wire

from . import zip32
from .address import encode_unified, encode_transparent, P2PKH,\
                     ORCHARD, MAINNET, TESTNET, SLIP44_COIN_TYPES

if False:
    from trezor.wire import Context

SLIP44_COIN_TYPES = (MAINNET, TESTNET)
BIP44_SCHEMA = PathSchema.parse(PATTERN_BIP44, SLIP44_COIN_TYPES)

async def get_address(ctx: Context, msg: ZcashGetAddress) -> ZcashAddress:
    has_t_addr = len(msg.t_address_n) != 0
    has_z_addr = len(msg.z_address_n) != 0

    if not (has_t_addr or has_z_addr):
        raise wire.DataError("t-address or z-address expected")
    
    if has_z_addr:
        receivers = dict()
        receivers[ORCHARD] = await get_orchard_raw_address(ctx, msg)

        if has_t_addr: 
            if msg.z_address_n[1] != msg.t_address_n[1]:
                raise wire.DataError("SLIP-44 coin_type of addresses differs.")
            receivers[P2PKH] = await get_transparent_raw_address(ctx, msg)
            title = "" # no title for unified address
        else:
            title = address_n_to_str(msg.z_address_n)

        coin_type = msg.z_address_n[1]^HARDENED
        address = encode_unified(receivers, coin_type)

    else: # has only t-address
        title = address_n_to_str(msg.t_address_n)
        raw_address = await get_transparent_raw_address(ctx, msg)
        coin_type = msg.t_address_n[1]^HARDENED
        address = encode_transparent(raw_address, coin_type)

    # TODO: QR code overflows for Orchard+P2PKH addresses
    if msg.show_display:
        await show_address(
            ctx, address=address, address_qr=address, title=title
        )

    return ZcashAddress(address=address)

async def get_transparent_raw_address(ctx: Context, msg: GetZcashAddress):
    """Returns Zcash raw P2PKH transparent address."""
    # I ommit `slip21_namespaces = [[b"SLIP-0019"]]`.
    keychain = await get_keychain(ctx, "secp256k1", (BIP44_SCHEMA,))    
    keychain.verify_path(msg.t_address_n)
    node = keychain.derive(msg.t_address_n)
    return sha256_ripemd160(node.public_key()).digest()

async def get_orchard_raw_address(ctx: Context, msg: GetZcashAddress):
    """Returns raw Zcash Orchard address"""   
    zip32.verify_path(msg.z_address_n)
    master = await zip32.get_master(ctx)
    sk = master.derive(msg.z_address_n).spending_key()

    return zcash.get_orchard_address(sk, msg.diversifier_index)
