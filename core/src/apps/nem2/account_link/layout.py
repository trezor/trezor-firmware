from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    NEM2TransactionCommon,
    NEM2EmbeddedTransactionCommon,
    NEM2AccountLinkTransaction
)

from trezor.ui.text import Text
from trezor.ui.scroll import Paginated

from ..layout import require_confirm_final, require_confirm_text

from apps.common.confirm import require_confirm
from apps.common.layout import split_address

async def ask_account_link(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    account_link: NEM2AccountLinkTransaction,
    embedded=False
):

    properties = []

    # Remote Public Key
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Remote Public Key:")
    t.mono(*split_address(account_link.remote_public_key.upper()))
    t.br()
    properties.append(t)

    # Link Action
    link_action_text = "Link" if account_link.link_action == 1 else "Unlink"
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Link Action:")
    t.br()
    t.normal('{}'.format(link_action_text))
    properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

    if not embedded:
        await require_confirm_final(ctx, common.max_fee)