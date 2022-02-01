from ubinascii import hexlify

from trezor import strings, ui
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import (
    confirm_action,
    confirm_blob,
    confirm_output,
    confirm_properties,
    confirm_text,
)
from trezor import ui
from trezor.ui.layouts.tt import Confirm, raise_if_cancelled, interact
from trezor.ui.constants.tt import MONO_ADDR_PER_LINE, MONO_HEX_PER_LINE
from trezor.utils import chunks_intersperse, chunks
from trezor.ui.components.tt.text import Text
from trezor.ui.components.tt.scroll import paginate_paragraphs, Paginated
from apps.common.paths import address_n_to_str

from apps.bitcoin.sign_tx import helpers

def _format_amount(value):
    return "%s ZEC" % strings.format_amount(value, 8)

class UiConfirmOrchardOutput(helpers.UiConfirm):
    def __init__(self, txo, multi_acount):
        self.txo = txo
        self.multi_acount = multi_acount

    # def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
    def confirm_dialog(self, ctx):
        pages = []
        pages.append(self.get_pay_page())
        pages.append(self.get_properties_page())
        pages.extend(self.get_memo_pages())
        #pages.extend(self.get_undecryptability_pages())

        pages[-1] = Confirm(pages[-1], cancel="Cancel")

        if len(pages) == 1:
            content = pages[0]
        else:
            content = Paginated(pages)

        return raise_if_cancelled(interact(
            ctx,
            content,
            "confirm_orchard_output",
        ))

    def get_pay_page(self):
        text = Text("Confirm sending", ui.ICON_SEND, ui.GREEN, new_lines=False)
        text.bold(_format_amount(self.txo.amount))
        text.normal(" to\n")
        # TODO: refuse long addresses
        if orchard_output_is_change(self.txo):
            text.mono("acount")
            account = self.txo.address_n[2] ^ (1<<31)
            text.bold(" #" + str(account))
            #text.br()
            #text.mono(address_n_to_str(self.txo.address_n))
        else:
            address = self.txo.address[:26]+"..."
            text.mono(*chunks_intersperse(address, MONO_ADDR_PER_LINE))

        return text

    def get_properties_page(self):
        properties = dict()
        properties["memo"] = "yes" if self.txo.orchard.memo is not None else "no"
        if self.txo.orchard.decryptable:
            if self.multi_acount:
                account = self.txo.orchard.ovk_address_n[2] ^ (1<<31)
                properties["decryptable"] = "by account #" + str(account)
            else:
                properties["decryptable"] = "yes"
        else:
            properties["decryptable"] = "no"

        text = Text("with properties", ui.ICON_SEND, ui.GREEN, new_lines=False)
        for key, value in properties.items():
            text.bold(key, ": ")
            text.normal(value, "\n")
        return text


    def get_memo_pages(self):
        # TODO: recipient included tag 
        if self.txo.orchard.memo is None:
            return []
            #text = Text("without memo", ui.ICON_SEND, ui.GREEN, new_lines=False)
            #return [text]

        try:
            memo = self.txo.orchard.memo.decode()
        except UnicodeDecodeError:
            memo = hexlify(self.txo.orchard.memo).decode()


        lines = [(ui.MONO, line) for line in chunks(memo, MONO_HEX_PER_LINE - 2)]

        paginated = paginate_paragraphs(
            lines,
            "with memo",
            header_icon=ui.ICON_SEND,
            icon_color=ui.GREEN,
            confirm=lambda x: x
        )

        if isinstance(paginated, Text):
            return [paginated]
        elif isinstance(paginated, Paginated):
            return paginated.pages

    def get_undecryptability_pages(self):
        if self.txo.orchard.decryptable:
            return []
        text = Text("without possibility", ui.ICON_WIPE, ui.RED, new_lines=False)
        text.content.append(ui.GREY)
        text.bold("to decrypt this output\n")
        text.bold("by Outgoing Viewing\n")
        text.bold("Key\n")
        return [text]

    """
    def get_ovk_pages(self):
        if not self.multiple_input_accounts:
            return []
        text = Text("decryptable by", ui.ICON_SEND, ui.GREEN, new_lines=False)
        text.mono("acount\n")
        text.mono(address_n_to_str(self.txo.orchard.ovk_address_n))
        return [text]
    """


def orchard_output_is_change(txo):
    return len(txo.address_n) != 0

async def require_confirm_export_fvk(ctx):
    await confirm_action(
        ctx,
        "get_full_viewing_key",
        "Confirm export",
        description="Do you really want to export Full Viewing Key?",
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )

async def require_confirm_export_ivk(ctx):
    await confirm_action(
        ctx,
        "get_incoming_viewing_key",
        "Confirm export",
        description="Do you really want to export Incoming Viewing Key?",
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )