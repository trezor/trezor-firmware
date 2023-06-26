from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import GetPublicKey, PublicKey
    from trezor.protobuf import MessageType


async def get_public_key(
    msg: GetPublicKey, auth_msg: MessageType | None = None
) -> PublicKey:
    from trezor import wire
    from trezor.enums import InputScriptType
    from trezor.messages import HDNodeType, PublicKey, UnlockPath

    from apps.common import coininfo, paths
    from apps.common.keychain import FORBIDDEN_KEY_PATH, get_keychain

    coin_name = msg.coin_name or "Bitcoin"
    script_type = msg.script_type or InputScriptType.SPENDADDRESS
    coin = coininfo.by_name(coin_name)
    curve_name = msg.ecdsa_curve_name or coin.curve_name
    address_n = msg.address_n  # local_cache_attribute
    ignore_xpub_magic = msg.ignore_xpub_magic  # local_cache_attribute
    xpub_magic = coin.xpub_magic  # local_cache_attribute

    if address_n and address_n[0] == paths.SLIP25_PURPOSE:
        # UnlockPath is required to access SLIP25 paths.
        if not UnlockPath.is_type_of(auth_msg):
            raise FORBIDDEN_KEY_PATH

        # Verify that the desired path lies in the unlocked subtree.
        if auth_msg.address_n != address_n[: len(auth_msg.address_n)]:
            raise FORBIDDEN_KEY_PATH

    keychain = await get_keychain(curve_name, [paths.AlwaysMatchingSchema])

    node = keychain.derive(address_n)

    if (
        script_type
        in (
            InputScriptType.SPENDADDRESS,
            InputScriptType.SPENDMULTISIG,
            InputScriptType.SPENDTAPROOT,
        )
        and xpub_magic is not None
    ):
        node_xpub = node.serialize_public(xpub_magic)
    elif (
        coin.segwit
        and script_type == InputScriptType.SPENDP2SHWITNESS
        and (ignore_xpub_magic or coin.xpub_magic_segwit_p2sh is not None)
    ):
        assert coin.xpub_magic_segwit_p2sh is not None
        node_xpub = node.serialize_public(
            xpub_magic if ignore_xpub_magic else coin.xpub_magic_segwit_p2sh
        )
    elif (
        coin.segwit
        and script_type == InputScriptType.SPENDWITNESS
        and (ignore_xpub_magic or coin.xpub_magic_segwit_native is not None)
    ):
        assert coin.xpub_magic_segwit_native is not None
        node_xpub = node.serialize_public(
            xpub_magic if ignore_xpub_magic else coin.xpub_magic_segwit_native
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

        await show_xpub(node_xpub, "XPUB")

    return PublicKey(
        node=node_type,
        xpub=node_xpub,
        root_fingerprint=keychain.root_fingerprint(),
    )
