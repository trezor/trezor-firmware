from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.TezosPublicKey import TezosPublicKey
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.common import seed
from apps.common.confirm import require_confirm
from apps.tezos.helpers import TEZOS_CURVE, TEZOS_PUBLICKEY_PREFIX, base58_encode_check


async def get_public_key(ctx, msg):
    address_n = msg.address_n or ()
    node = await seed.derive_node(ctx, address_n, TEZOS_CURVE)

    pk = seed.remove_ed25519_prefix(node.public_key())
    pk_prefixed = base58_encode_check(pk, prefix=TEZOS_PUBLICKEY_PREFIX)

    if msg.show_display:
        await _show_tezos_pubkey(ctx, pk_prefixed)

    return TezosPublicKey(public_key=pk_prefixed)


async def _show_tezos_pubkey(ctx, pubkey):
    lines = chunks(pubkey, 18)
    text = Text("Confirm public key", ui.ICON_RECEIVE, icon_color=ui.GREEN)
    text.mono(*lines)
    return await require_confirm(ctx, text, code=ButtonRequestType.PublicKey)
