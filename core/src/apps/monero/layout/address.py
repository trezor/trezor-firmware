from micropython import const

from trezor import loop, ui, wire
from trezor.messages import ButtonRequestType
from trezor.ui.button import ButtonDefault
from trezor.ui.confirm import CONFIRMED, Confirm
from trezor.ui.container import Container
from trezor.ui.qr import Qr
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.wire import Context

from apps.common import button_request
from apps.common.confirm import confirm
from apps.monero.layout import common

if False:
    from typing import Optional, Tuple

if __debug__:
    from apps.debug import swipe_signal


async def show_address(
    ctx, address: str, desc: str = "Confirm address", network: str = None
):
    pages = []
    for lines in common.paginate_lines(common.split_address(address), 5):
        text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
        if network is not None:
            text.normal("%s network" % network)
        text.mono(*lines)
        pages.append(text)

    return await confirm(
        ctx,
        Paginated(pages),
        code=ButtonRequestType.Address,
        cancel="QR",
        cancel_style=ButtonDefault,
    )


def render_scrollbar(pages: int, page: int) -> None:
    BBOX = const(220)
    SIZE = const(8)

    padding = 14
    if pages * padding > BBOX:
        padding = BBOX // pages

    X = const(232)
    Y = (BBOX // 2) - (pages // 2) * padding

    for i in range(0, pages):
        if i == page:
            fg = ui.FG
        else:
            fg = ui.GREY
        ui.display.bar_radius(X, Y + i * padding, SIZE, SIZE, fg, ui.BG, 4)


class ZoomingQrConfirm(Confirm):
    def __init__(
        self,
        ctx: Context,
        qr_data: str,
        qr_text: Optional[str],
        cancel: str,
        qr_scales: Tuple[int] = (3, 5),
    ) -> None:
        self.ctx = ctx
        self.qr_data = qr_data
        self.qr_text = qr_text
        self.qr_scales = qr_scales
        self.cur_scale = len(qr_scales) - 1
        self.content = None  # type: Optional[ui.Component]
        self.confirm_orig = None
        self.cancel_orig = None
        self.gen_qr()
        super().__init__(
            self.content,
            confirm=Confirm.DEFAULT_CONFIRM,
            confirm_style=Confirm.DEFAULT_CONFIRM_STYLE,
            cancel=cancel,
            cancel_style=ButtonDefault,
            major_confirm=False,
        )
        self.confirm_orig = self.confirm
        self.cancel_orig = self.cancel

    async def show(self):
        await button_request(self.ctx, code=ButtonRequestType.Address)
        return await self.ctx.wait(self) is CONFIRMED

    def dispatch(self, event: int, x: int, y: int) -> None:
        super().dispatch(event, x, y)
        self.content.dispatch(event, x, y)
        if event is ui.RENDER:
            render_scrollbar(len(self.qr_scales), self.cur_scale)

    def gen_qr(self):
        QR_X = const(120)
        QR_Y = const(115)
        self.cur_scale = (self.cur_scale + 1) % len(self.qr_scales)
        qr = Qr(self.qr_data, QR_X, QR_Y, self.qr_scales[self.cur_scale])
        text = Text(self.qr_text, ui.ICON_RECEIVE, ui.GREEN) if self.qr_text else None
        self.content = Container(qr, text) if text else qr

        # Show buttons only for the small QR code
        if self.cur_scale == 0:
            self.cancel = self.cancel_orig
            self.confirm = self.confirm_orig
        else:
            self.cancel = None
            self.confirm = None

    async def handle_paging(self) -> None:
        from trezor.ui.swipe import SWIPE_ALL, Swipe

        directions = SWIPE_ALL

        if __debug__:
            _ = await loop.race(Swipe(directions), swipe_signal())
        else:
            _ = await Swipe(directions)

        self.gen_qr()
        self.content.repaint = True

    def create_tasks(self) -> Tuple[loop.Task, ...]:
        tasks = super().create_tasks()
        return tasks + (self.handle_paging(),)


async def show_qr(
    ctx: wire.Context,
    address: str,
    desc: str = "Confirm address",
    cancel: str = "Address",
) -> bool:
    content = ZoomingQrConfirm(ctx, address, desc, cancel)
    return await content.show()
