from trezor import wire
from trezor.messages import InputScriptType
from trezor.messages.HDNodeType import HDNodeType
from trezor.messages.PublicKey import PublicKey

from apps.common import HARDENED, coins, layout, seed

from .keychain import get_keychain_for_coin


async def get_keychain_for_curve(ctx: wire.Context, curve_name: str) -> seed.Keychain:
    """Set up a keychain for SLIP-13 and SLIP-17 namespaces with a specified curve."""
    namespaces = [
        (curve_name, [13 | HARDENED]),
        (curve_name, [17 | HARDENED]),
    ]
    return await seed.get_keychain(ctx, namespaces)


async def get_public_key(ctx, msg):
    coin_name = msg.coin_name or "Bitcoin"
    script_type = msg.script_type or InputScriptType.SPENDADDRESS

    if msg.ecdsa_curve_name is not None:
        # If a curve name is provided, disallow coin-specific features.
        if (
            msg.coin_name is not None
            or msg.script_type is not InputScriptType.SPENDADDRESS
        ):
            raise wire.DataError(
                "Cannot use coin_name or script_type with ecdsa_curve_name"
            )

        coin = coins.by_name("Bitcoin")
        # only allow SLIP-13/17 namespaces
        keychain = await get_keychain_for_curve(ctx, msg.ecdsa_curve_name)

    elif (
        coin_name == "Bitcoin"
        and script_type is InputScriptType.SPENDADDRESS
        and msg.address_n in ([HARDENED], [0])
    ):
        # allow extracting PSBT master fingerprinty by calling GetPublicKey(m/0')
        coin = coins.by_name("Bitcoin")
        keychain = await seed.get_keychain(
            ctx, [("secp256k1", [HARDENED]), ("secp256k1", [0])]
        )

    else:
        # select curve and namespaces based on the requested coin properties
        keychain, coin = await get_keychain_for_coin(ctx, msg.coin_name)

    node = keychain.derive(msg.address_n)

    if (
        script_type in [InputScriptType.SPENDADDRESS, InputScriptType.SPENDMULTISIG]
        and coin.xpub_magic is not None
    ):
        node_xpub = node.serialize_public(coin.xpub_magic)
    elif (
        coin.segwit
        and script_type == InputScriptType.SPENDP2SHWITNESS
        and coin.xpub_magic_segwit_p2sh is not None
    ):
        node_xpub = node.serialize_public(coin.xpub_magic_segwit_p2sh)
    elif (
        coin.segwit
        and script_type == InputScriptType.SPENDWITNESS
        and coin.xpub_magic_segwit_native is not None
    ):
        node_xpub = node.serialize_public(coin.xpub_magic_segwit_native)
    else:
        raise wire.DataError("Invalid combination of coin and script_type")

    pubkey = node.public_key()
    if pubkey[0] == 1:
        pubkey = b"\x00" + pubkey[1:]
    node_type = HDNodeType(
        depth=node.depth(),
        child_num=node.child_num(),
        fingerprint=node.fingerprint(),
        chain_code=node.chain_code(),
        public_key=pubkey,
    )

    if msg.show_display:
        await layout.show_pubkey(ctx, pubkey)

    return PublicKey(node=node_type, xpub=node_xpub)
