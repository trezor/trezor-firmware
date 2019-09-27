from micropython import const

from trezor import loop, res, ui
from trezor.ui.button import Button, ButtonCancel, ButtonConfirm, ButtonDefault
from trezor.ui.loader import Loader, LoaderDefault

if __debug__:
    from apps.debug import swipe_signal

if False:
    from typing import Any, Optional, List, Tuple
    from trezor.ui.button import ButtonContent, ButtonStyleType
    from trezor.ui.loader import LoaderStyleType

CONFIRMED = object()
CANCELLED = object()
INFO = object()


class Confirm(ui.Layout):
    DEFAULT_CONFIRM = res.load(ui.ICON_CONFIRM)
    DEFAULT_CONFIRM_STYLE = ButtonConfirm
    DEFAULT_CANCEL = res.load(ui.ICON_CANCEL)
    DEFAULT_CANCEL_STYLE = ButtonCancel

    def __init__(
        self,
        content: ui.Component,
        confirm: Optional[ButtonContent] = DEFAULT_CONFIRM,
        confirm_style: ButtonStyleType = DEFAULT_CONFIRM_STYLE,
        cancel: Optional[ButtonContent] = DEFAULT_CANCEL,
        cancel_style: ButtonStyleType = DEFAULT_CANCEL_STYLE,
        major_confirm: bool = False,
    ) -> None:
        self.content = content

        if confirm is not None:
            if cancel is None:
                area = ui.grid(4, n_x=1)
            elif major_confirm:
                area = ui.grid(13, cells_x=2)
            else:
                area = ui.grid(9, n_x=2)
            self.confirm = Button(
                area, confirm, confirm_style
            )  # type: Optional[Button]
            self.confirm.on_click = self.on_confirm  # type: ignore
        else:
            self.confirm = None

        if cancel is not None:
            if confirm is None:
                area = ui.grid(4, n_x=1)
            elif major_confirm:
                area = ui.grid(12, cells_x=1)
            else:
                area = ui.grid(8, n_x=2)
            self.cancel = Button(area, cancel, cancel_style)  # type: Optional[Button]
            self.cancel.on_click = self.on_cancel  # type: ignore
        else:
            self.cancel = None

    def dispatch(self, event: int, x: int, y: int) -> None:
        super().dispatch(event, x, y)
        self.content.dispatch(event, x, y)
        if self.confirm is not None:
            self.confirm.dispatch(event, x, y)
        if self.cancel is not None:
            self.cancel.dispatch(event, x, y)

    def on_confirm(self) -> None:
        raise ui.Result(CONFIRMED)

    def on_cancel(self) -> None:
        raise ui.Result(CANCELLED)

    if __debug__:

        def read_content(self) -> List[str]:
            return self.content.read_content()


class Pageable:
    def __init__(self) -> None:
        self._page = 0

    def page(self) -> int:
        return self._page

    def page_count(self) -> int:
        raise NotImplementedError

    def is_first(self) -> bool:
        return self._page == 0

    def is_last(self) -> bool:
        return self._page == self.page_count() - 1

    def next(self) -> None:
        self._page = min(self._page + 1, self.page_count() - 1)

    def prev(self) -> None:
        self._page = max(self._page - 1, 0)


class ConfirmPageable(Confirm):
    def __init__(self, pageable: Pageable, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.pageable = pageable

    async def handle_paging(self) -> None:
        from trezor.ui.swipe import SWIPE_HORIZONTAL, SWIPE_LEFT, SWIPE_RIGHT, Swipe

        if self.pageable.is_first():
            directions = SWIPE_LEFT
        elif self.pageable.is_last():
            directions = SWIPE_RIGHT
        else:
            directions = SWIPE_HORIZONTAL

        if __debug__:
            swipe = await loop.race(Swipe(directions), swipe_signal())
        else:
            swipe = await Swipe(directions)

        if swipe == SWIPE_LEFT:
            self.pageable.next()
        else:
            self.pageable.prev()

        self.content.repaint = True
        if self.confirm is not None:
            self.confirm.repaint = True
        if self.cancel is not None:
            self.cancel.repaint = True

    def create_tasks(self) -> Tuple[loop.Task, ...]:
        tasks = super().create_tasks()
        if self.pageable.page_count() > 1:
            return tasks + (self.handle_paging(),)
        else:
            return tasks

    def on_render(self) -> None:
        PULSE_PERIOD = const(1200000)

        super().on_render()

        if not self.pageable.is_first():
            t = ui.pulse(PULSE_PERIOD)
            c = ui.blend(ui.GREY, ui.DARK_GREY, t)
            icon = res.load(ui.ICON_SWIPE_RIGHT)
            ui.display.icon(18, 68, icon, c, ui.BG)

        if not self.pageable.is_last():
            t = ui.pulse(PULSE_PERIOD, PULSE_PERIOD // 2)
            c = ui.blend(ui.GREY, ui.DARK_GREY, t)
            icon = res.load(ui.ICON_SWIPE_LEFT)
            ui.display.icon(205, 68, icon, c, ui.BG)


class InfoConfirm(ui.Layout):
    DEFAULT_CONFIRM = res.load(ui.ICON_CONFIRM)
    DEFAULT_CONFIRM_STYLE = ButtonConfirm
    DEFAULT_CANCEL = res.load(ui.ICON_CANCEL)
    DEFAULT_CANCEL_STYLE = ButtonCancel
    DEFAULT_INFO = res.load(ui.ICON_CLICK)  # TODO: this should be (i) icon, not click
    DEFAULT_INFO_STYLE = ButtonDefault

    def __init__(
        self,
        content: ui.Component,
        confirm: ButtonContent = DEFAULT_CONFIRM,
        confirm_style: ButtonStyleType = DEFAULT_CONFIRM_STYLE,
        cancel: ButtonContent = DEFAULT_CANCEL,
        cancel_style: ButtonStyleType = DEFAULT_CANCEL_STYLE,
        info: ButtonContent = DEFAULT_INFO,
        info_style: ButtonStyleType = DEFAULT_INFO_STYLE,
    ) -> None:
        self.content = content

        self.confirm = Button(ui.grid(14), confirm, confirm_style)
        self.confirm.on_click = self.on_confirm  # type: ignore

        self.info = Button(ui.grid(13), info, info_style)
        self.info.on_click = self.on_info

        self.cancel = Button(ui.grid(12), cancel, cancel_style)
        self.cancel.on_click = self.on_cancel  # type: ignore

    def dispatch(self, event: int, x: int, y: int) -> None:
        self.content.dispatch(event, x, y)
        if self.confirm is not None:
            self.confirm.dispatch(event, x, y)
        if self.cancel is not None:
            self.cancel.dispatch(event, x, y)
        if self.info is not None:
            self.info.dispatch(event, x, y)

    def on_confirm(self) -> None:
        raise ui.Result(CONFIRMED)

    def on_cancel(self) -> None:
        raise ui.Result(CANCELLED)

    def on_info(self) -> None:
        raise ui.Result(INFO)

    if __debug__:

        def read_content(self) -> List[str]:
            return self.content.read_content()


class HoldToConfirm(ui.Layout):
    DEFAULT_CONFIRM = "Hold To Confirm"
    DEFAULT_CONFIRM_STYLE = ButtonConfirm
    DEFAULT_LOADER_STYLE = LoaderDefault

    def __init__(
        self,
        content: ui.Component,
        confirm: str = DEFAULT_CONFIRM,
        confirm_style: ButtonStyleType = DEFAULT_CONFIRM_STYLE,
        loader_style: LoaderStyleType = DEFAULT_LOADER_STYLE,
    ):
        self.content = content

        self.loader = Loader(loader_style)
        self.loader.on_start = self._on_loader_start  # type: ignore

        self.button = Button(ui.grid(4, n_x=1), confirm, confirm_style)
        self.button.on_press_start = self._on_press_start  # type: ignore
        self.button.on_press_end = self._on_press_end  # type: ignore
        self.button.on_click = self._on_click  # type: ignore

    def _on_press_start(self) -> None:
        self.loader.start()

    def _on_press_end(self) -> None:
        self.loader.stop()

    def _on_loader_start(self) -> None:
        # Loader has either started growing, or returned to the 0-position.
        # In the first case we need to clear the content leftovers, in the latter
        # we need to render the content again.
        ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT - 60, ui.BG)
        self.content.dispatch(ui.REPAINT, 0, 0)

    def _on_click(self) -> None:
        if self.loader.elapsed_ms() >= self.loader.target_ms:
            self.on_confirm()

    def dispatch(self, event: int, x: int, y: int) -> None:
        if self.loader.start_ms is not None:
            self.loader.dispatch(event, x, y)
        else:
            self.content.dispatch(event, x, y)
        self.button.dispatch(event, x, y)

    def on_confirm(self) -> None:
        raise ui.Result(CONFIRMED)

    if __debug__:

        def read_content(self) -> List[str]:
            return self.content.read_content()
