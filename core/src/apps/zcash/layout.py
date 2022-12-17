from typing import TYPE_CHECKING

from trezor import strings, ui
from trezor.enums import ButtonRequestType
from trezor.ui.components.common.confirm import CONFIRMED, SHOW_PAGINATED
from trezor.ui.components.tt.scroll import AskPaginated, Paginated, paginate_paragraphs
from trezor.ui.components.tt.text import Text
from trezor.ui.constants.tt import MONO_ADDR_PER_LINE
from trezor.ui.layouts import confirm_address, confirm_metadata
from trezor.ui.layouts.tt import Confirm, interact, raise_if_cancelled
from trezor.utils import chunks, chunks_intersperse, ensure

from apps.bitcoin.sign_tx.helpers import UiConfirm
from apps.common import paths

if TYPE_CHECKING:
    from typing import Awaitable, Any
    from apps.common.coininfo import CoinInfo
    from trezor.wire import Context
    from trezor.messages import ZcashOrchardOutput, TxOutput
    from trezor.ui import Component
    from trezor.ui.layouts.common import LayoutType


class UiConfirmForeignPath(UiConfirm):
    def __init__(self, path: paths.Bip32Path):
        self.path = path

    def confirm_dialog(self, ctx: Context) -> Awaitable[Any]:
        return paths.show_path_warning(ctx, self.path)


class ConfirmOrchardInputsCountOverThreshold(UiConfirm):
    def __init__(self, orchard_inputs_count):
        self.orchard_inputs_count = orchard_inputs_count

    def confirm_dialog(self, ctx: Context) -> Awaitable[Any]:
        return confirm_metadata(
            ctx,
            "orchard_inputs_count_over_threshold",
            "Warning",
            "There are {}\nshielded inputs.",
            str(self.orchard_inputs_count),
            ButtonRequestType.SignTx,
        )


def _format_amount(value: int, coin: CoinInfo) -> str:
    return "%s %s" % (strings.format_amount(value, 8), coin.coin_shortcut)


class UiConfirmTransparentOutput(UiConfirm):
    def __init__(self, txo: TxOutput, coin: CoinInfo) -> None:
        self.txo = txo
        self.coin = coin

    def confirm_dialog(self, ctx: Context) -> Awaitable[Any]:
        content = Confirm(get_pay_page(self.txo, self.coin, "t"))
        assert self.txo.address is not None  # typing
        return maybe_show_full_address(
            ctx, content, self.txo.address, ButtonRequestType.ConfirmOutput
        )


class UiConfirmOrchardOutput(UiConfirm):
    def __init__(self, txo: ZcashOrchardOutput, coin: CoinInfo) -> None:
        self.txo = txo
        self.coin = coin

    def confirm_dialog(self, ctx: Context) -> Awaitable[Any]:
        pages = []
        pages.append(get_pay_page(self.txo, self.coin, "z"))
        pages.extend(get_memo_pages(self.txo.memo))

        pages[-1] = Confirm(pages[-1])

        assert len(pages) >= 2  # pay page + memo page
        content = Paginated(pages)
        assert self.txo.address is not None  # typing
        return maybe_show_full_address(
            ctx, content, self.txo.address, ButtonRequestType.ConfirmOutput
        )


def get_pay_page(
    txo: TxOutput | ZcashOrchardOutput, coin: CoinInfo, transfer_type: str
) -> Component:
    assert transfer_type in ("t", "z")
    title = "Confirm %s-sending" % transfer_type
    text = Text(title, ui.ICON_SEND, ui.GREEN, new_lines=False)
    text.bold(_format_amount(txo.amount, coin))
    text.normal(" to\n")

    assert txo.address is not None  # typing
    if txo.address.startswith("t"):  # transparent address
        ensure(len(txo.address) == 35)
        text.mono(*chunks_intersperse(txo.address, MONO_ADDR_PER_LINE))
        return text
    elif txo.address.startswith("u"):  # unified address
        address_lines = chunks(txo.address, MONO_ADDR_PER_LINE)
        text.mono(next(address_lines) + "\n")
        text.mono(next(address_lines)[:-3] + "...")
        return AskPaginated(text, "show full address")
    else:
        raise ValueError("Unexpected address prefix.")


def get_memo_pages(memo: str | None) -> list[Component]:
    if memo is None:
        return [Text("without memo", ui.ICON_SEND, ui.GREEN)]

    paginated = paginate_paragraphs(
        [(ui.NORMAL, memo)],
        "with memo",
        header_icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
    )

    if isinstance(paginated, Confirm):
        return [paginated.content]
    else:
        assert isinstance(paginated, Paginated)
        return paginated.pages


async def maybe_show_full_address(
    ctx: Context, content: LayoutType, full_address: str, br_code: ButtonRequestType
) -> None:
    """Lets user to toggle between output-confirmation-dialog
    and see-full-address-dialog before he confirms an output."""
    while True:
        result = await raise_if_cancelled(
            interact(
                ctx,
                content,
                "confirm_output",
                br_code,
            )
        )
        if result is SHOW_PAGINATED:
            await confirm_address(
                ctx,
                "Confirm address",
                full_address,
                description=None,
            )
        else:
            assert result is CONFIRMED
            break
