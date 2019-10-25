from trezor.crypto import base58
from trezor.crypto.curve import curve25519
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.VsysPublicKey import VsysPublicKey
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.common import paths, seed
from apps.common.confirm import require_confirm
from apps.vsys import CURVE, helpers
from apps.vsys.constants import ACCOUNT_API_VER, PROTOCOL, OPC_ACCOUNT


async def get_public_key(ctx, msg, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n, CURVE)
    sk = helpers.modify_private_key(node.private_key())
    pk = curve25519.publickey(sk)
    pk_base58 = base58.encode(pk)
    chain_id = helpers.get_chain_id(msg.address_n)
    address = helpers.get_address_from_public_key(pk_base58, chain_id)

    if msg.show_display:
        await _show_vsys_pubkey(ctx, pk_base58)

    return VsysPublicKey(api=ACCOUNT_API_VER,public_key=pk_base58, address=address, protocol=PROTOCOL, opc=OPC_ACCOUNT)


async def _show_vsys_pubkey(ctx, pubkey):
    lines = chunks(pubkey, 18)
    text = Text("Confirm public key", ui.ICON_RECEIVE, ui.GREEN)
    text.mono(*lines)
    return await require_confirm(ctx, text, code=ButtonRequestType.PublicKey)
