from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.crypto import bip32
    from trezor.enums import InputScriptType
    from trezor.messages import GetPublicKey, PublicKey
    from trezor.protobuf import MessageType

    from apps.common.keychain import Keychain


async def get_public_key(
    msg: GetPublicKey,
    auth_msg: MessageType | None = None,
    keychain: Keychain | None = None,
) -> PublicKey:
    from trezor import TR, wire
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

    if not keychain:
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
    # For curve25519 and ed25519, the public key has the prefix 0x00, as specified by SLIP-10. However, since this prefix is non-standard, it may be removed in the future.
    node_type = HDNodeType(
        depth=node.depth(),
        child_num=node.child_num(),
        fingerprint=node.fingerprint(),
        chain_code=node.chain_code(),
        public_key=pubkey,
    )
    descriptor = _xpub_descriptor(
        node, xpub_magic, address_n, script_type, keychain.root_fingerprint()
    )

    if msg.show_display:
        from trezor.ui.layouts import confirm_path_warning, show_pubkey

        from apps.common.paths import address_n_to_str

        from .keychain import address_n_to_name

        path = address_n_to_str(address_n)
        account_name = address_n_to_name(
            coin, address_n, script_type, account_level=True
        )
        if account_name is None:
            account = None
            await confirm_path_warning(path)
        elif account_name == "":
            account = coin.coin_shortcut
        else:
            account = f"{coin.coin_shortcut} {account_name}"
        show_xpub = node_xpub
        if script_type == InputScriptType.SPENDTAPROOT and descriptor is not None:
            show_xpub = descriptor
        await show_pubkey(
            show_xpub,
            "XPUB",
            account=account,
            path=path,
            mismatch_title=TR.addr_mismatch__xpub_mismatch,
            br_name="show_xpub",
        )

    return PublicKey(
        node=node_type,
        xpub=node_xpub,
        root_fingerprint=keychain.root_fingerprint(),
        descriptor=descriptor,
    )


def _xpub_descriptor(
    node: bip32.HDNode,
    xpub_magic: int,
    address_n: list[int],
    script_type: InputScriptType,
    fingerprint: int,
) -> str | None:
    from trezor.enums import InputScriptType

    from apps.common import paths

    from .common import descriptor_checksum

    if script_type == InputScriptType.SPENDADDRESS:
        fmt = "pkh({})"
    elif script_type == InputScriptType.SPENDP2SHWITNESS:
        fmt = "sh(wpkh({}))"
    elif script_type == InputScriptType.SPENDWITNESS:
        fmt = "wpkh({})"
    elif script_type == InputScriptType.SPENDTAPROOT:
        fmt = "tr({})"
    else:
        return None

    # always ignore script-dependent xpub magic for descriptors
    xpub = node.serialize_public(xpub_magic)

    path = paths.address_n_to_str(address_n).replace("'", "h")
    inner = f"[{fingerprint:08x}{path[1:]}]{xpub}/<0;1>/*"
    descriptor = fmt.format(inner)
    checksum = descriptor_checksum(descriptor)
    return f"{descriptor}#{checksum}"
