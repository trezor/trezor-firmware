from trezor import wire
from trezor.messages import InputScriptType
from trezor.messages.HDNodeType import HDNodeType
from trezor.messages.PublicKey import PublicKey

from apps.common import coins, layout, seed


async def get_public_key(ctx, msg):
    coin_name = msg.coin_name or "Bitcoin"
    coin = coins.by_name(coin_name)
    script_type = msg.script_type or InputScriptType.SPENDADDRESS

    curve_name = msg.ecdsa_curve_name
    if not curve_name:
        curve_name = coin.curve_name
    node = await seed.derive_node(ctx, msg.address_n, curve_name=curve_name)

    if script_type == InputScriptType.SPENDADDRESS and coin.xpub_magic is not None:
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
