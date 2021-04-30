from trezor import wire
from trezor.messages import HDNodeType, InputScriptType, PublicKey
from trezor.ui.layouts import show_xpub

from apps.common import coins, paths
from apps.common.keychain import get_keychain

if False:
    from trezor.messages import GetPublicKey


async def get_public_key(ctx: wire.Context, msg: GetPublicKey) -> PublicKey:
    coin_name = msg.coin_name or "Bitcoin"
    script_type = msg.script_type or InputScriptType.SPENDADDRESS
    coin = coins.by_name(coin_name)
    curve_name = msg.ecdsa_curve_name or coin.curve_name

    keychain = await get_keychain(ctx, curve_name, [paths.AlwaysMatchingSchema])

    node = keychain.derive(msg.address_n)

    if (
        script_type in (InputScriptType.SPENDADDRESS, InputScriptType.SPENDMULTISIG)
        and coin.xpub_magic is not None
    ):
        node_xpub = node.serialize_public(coin.xpub_magic)
    elif (
        coin.segwit
        and script_type == InputScriptType.SPENDP2SHWITNESS
        and (msg.ignore_xpub_magic or coin.xpub_magic_segwit_p2sh is not None)
    ):
        # TODO: resolve type: ignore below
        node_xpub = node.serialize_public(
            coin.xpub_magic if msg.ignore_xpub_magic else coin.xpub_magic_segwit_p2sh  # type: ignore
        )
    elif (
        coin.segwit
        and script_type == InputScriptType.SPENDWITNESS
        and (msg.ignore_xpub_magic or coin.xpub_magic_segwit_native is not None)
    ):
        # TODO: resolve type: ignore below
        node_xpub = node.serialize_public(
            coin.xpub_magic if msg.ignore_xpub_magic else coin.xpub_magic_segwit_native  # type: ignore
        )
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
        await show_xpub(ctx, node_xpub, "XPUB", "Cancel")

    return PublicKey(
        node=node_type,
        xpub=node_xpub,
        root_fingerprint=keychain.root_fingerprint(),
    )
