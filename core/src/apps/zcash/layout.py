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
    def __init__(self, txo):
        self.txo = txo

    # def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
    def confirm_dialog(self, ctx):
        pages = []
        pages.append(self.get_pay_page())
        pages.append(self.get_properties_page())
        pages.extend(self.get_memo_pages())

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
        address = self.txo.address[:26]+"..."
        text.mono(*chunks_intersperse(address, MONO_ADDR_PER_LINE))

        return text

    def get_properties_page(self):
        properties = dict()
        properties["memo"] = "yes" if self.txo.memo is not None else "no"
        properties["decryptable"] = "yes"

        # TODO: `include reply-To` field ?

        text = Text("with properties", ui.ICON_SEND, ui.GREEN, new_lines=False)
        for key, value in properties.items():
            text.bold(key, ": ")
            text.normal(value, "\n")
        return text

    def get_memo_pages(self):
        if self.txo.memo is None:
            return []

        try:
            memo = self.txo.memo.rstrip(b"\x00").decode()
            font = ui.NORMAL
        except UnicodeDecodeError:
            font = ui.MONO
            memo = hexlify(self.txo.memo).decode()

        lines = [(font, line) for line in chunks(memo, MONO_HEX_PER_LINE - 2)]

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


class UiConfirmOrchardFlags(helpers.UiConfirm):
    def __init__(self, enable_spends, enable_outputs):
        self.enable_spends = enable_spends
        self.enable_outputs = enable_outputs

    # def confirm_dialog(self, ctx: wire.Context) -> Awaitable[Any]:
    async def confirm_dialog(self, ctx):
        await confirm_text(
            ctx,
            "confirm_orchard_flags",
            "Confirm Orchard flags",
            description="enable spends: {}\nenable outputs: {}".format(
                "true" if self.enable_spends else "false",
                "true" if self.enable_outputs else "false",
            ),
            br_code=ButtonRequestType.SignTx,
        )

async def require_confirm_export_fvk(ctx):
    await confirm_action(
        ctx,
        "export_full_viewing_key",
        "Confirm export",
        description="Do you really want to export Full Viewing Key?",
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )

async def require_confirm_export_ivk(ctx):
    await confirm_action(
        ctx,
        "export_incoming_viewing_key",
        "Confirm export",
        description="Do you really want to export Incoming Viewing Key?",
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )