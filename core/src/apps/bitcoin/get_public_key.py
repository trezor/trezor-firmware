from typing import TYPE_CHECKING

from trezor import wire
from trezor.enums import InputScriptType
from trezor.messages import HDNodeType, PublicKey, UnlockPath

from apps.common import coininfo, paths
from apps.common.keychain import FORBIDDEN_KEY_PATH, get_keychain

if TYPE_CHECKING:
    from trezor.messages import GetPublicKey
    from trezor.protobuf import MessageType


async def get_public_key(
    ctx: wire.Context, msg: GetPublicKey, auth_msg: MessageType | None = None
) -> PublicKey:
    coin_name = msg.coin_name or "Bitcoin"
    script_type = msg.script_type or InputScriptType.SPENDADDRESS
    coin = coininfo.by_name(coin_name)
    curve_name = msg.ecdsa_curve_name or coin.curve_name

    if msg.address_n and msg.address_n[0] == paths.SLIP25_PURPOSE:
        # UnlockPath is required to access SLIP25 paths.
        if not UnlockPath.is_type_of(auth_msg):
            raise FORBIDDEN_KEY_PATH

        # Verify that the desired path lies in the unlocked subtree.
        if auth_msg.address_n != msg.address_n[: len(auth_msg.address_n)]:
            raise FORBIDDEN_KEY_PATH

    keychain = await get_keychain(ctx, curve_name, [paths.AlwaysMatchingSchema])

    node = keychain.derive(msg.address_n)

    if (
        script_type
        in (
            InputScriptType.SPENDADDRESS,
            InputScriptType.SPENDMULTISIG,
            InputScriptType.SPENDTAPROOT,
        )
        and coin.xpub_magic is not None
    ):
        node_xpub = node.serialize_public(coin.xpub_magic)
    elif (
        coin.segwit
        and script_type == InputScriptType.SPENDP2SHWITNESS
        and (msg.ignore_xpub_magic or coin.xpub_magic_segwit_p2sh is not None)
    ):
        assert coin.xpub_magic_segwit_p2sh is not None
        node_xpub = node.serialize_public(
            coin.xpub_magic if msg.ignore_xpub_magic else coin.xpub_magic_segwit_p2sh
        )
    elif (
        coin.segwit
        and script_type == InputScriptType.SPENDWITNESS
        and (msg.ignore_xpub_magic or coin.xpub_magic_segwit_native is not None)
    ):
        assert coin.xpub_magic_segwit_native is not None
        node_xpub = node.serialize_public(
            coin.xpub_magic if msg.ignore_xpub_magic else coin.xpub_magic_segwit_native
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
        from trezor.ui.layouts import show_xpub

        await show_xpub(ctx, node_xpub, "XPUB", "Cancel")

    return PublicKey(
        node=node_type,
        xpub=node_xpub,
        root_fingerprint=keychain.root_fingerprint(),
    )
