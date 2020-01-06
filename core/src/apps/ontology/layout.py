from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.utils import chunks, format_amount

from apps.common.confirm import require_confirm


async def require_confirm_transfer_ont(ctx, dest, value):
    text = Text("Confirm sending", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold(format_amount(value, 0) + " ONT")
    text.mono(*split_address("To: " + dest))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_transfer_ong(ctx, dest, value):
    text = Text("Confirm sending", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold(format_amount(value, 9) + " ONG")
    text.mono(*split_address("To: " + dest))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_withdraw_ong(ctx, value):
    text = Text("Confirm withdraw of ", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold(format_amount(value, 9) + " ONG")
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_ont_id_register(ctx, ont_id, public_key):
    t = Text("Confirm registering", ui.ICON_SEND, ui.GREEN)
    key = hexlify(public_key).decode()
    t.normal("for " + ont_id + " with public key " + key)
    pages = [t]

    return await require_confirm(ctx, Paginated(pages), code=ButtonRequestType.SignTx)


async def require_confirm_ont_id_add_attributes(ctx, ont_id, public_key, attributes):
    key = hexlify(public_key).decode()
    t = Text("Confirm attributes", ui.ICON_SEND, ui.GREEN)
    t.normal("for " + ont_id + " with public key " + key)
    pages = [t]
    for attribute in attributes:
        t1 = Text("Attribute:")
        t1.normal("Name " + attribute.key)
        t1.normal("Type: " + attribute.type)
        t1.normal("Value: " + attribute.value)
        pages.append(t1)

    return await require_confirm(ctx, Paginated(pages), ButtonRequestType.SignTx)


def split_address(address):
    return chunks(address, 16)


def split_str(text: str):
    return list(chunks(text, 16))
