from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.TezosPublicKey import TezosPublicKey
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.common import seed
from apps.common.confirm import require_confirm
from apps.tezos.helpers import (
    b58cencode,
    get_curve_module,
    get_curve_name,
    get_pk_prefix,
)


async def tezos_get_public_key(ctx, msg):
    address_n = msg.address_n or ()
    curve = msg.curve or 0
    node = await seed.derive_node(ctx, address_n, get_curve_name(curve))

    sk = node.private_key()
    pk = get_curve_module(curve).publickey(sk)
    pk_prefixed = b58cencode(pk, prefix=get_pk_prefix(curve))

    if msg.show_display:
        await _show_tezos_pubkey(ctx, pk_prefixed)

    return TezosPublicKey(public_key=pk_prefixed)


async def _show_tezos_pubkey(ctx, pubkey):
    lines = chunks(pubkey, 18)
    text = Text("Confirm public key", ui.ICON_RECEIVE, icon_color=ui.GREEN)
    text.mono(*lines)
    return await require_confirm(ctx, text, code=ButtonRequestType.PublicKey)
