from trezor import res, ui
from trezor.ui.button import Button, ButtonCancel, ButtonConfirm
from trezor.ui.loader import Loader, LoaderDefault

if False:
    from trezor.ui.button import ButtonContent, ButtonStyleType
    from trezor.ui.loader import LoaderStyleType

CONFIRMED = object()
CANCELLED = object()


class Confirm(ui.Layout):
    DEFAULT_CONFIRM = res.load(ui.ICON_CONFIRM)
    DEFAULT_CONFIRM_STYLE = ButtonConfirm
    DEFAULT_CANCEL = res.load(ui.ICON_CANCEL)
    DEFAULT_CANCEL_STYLE = ButtonCancel

    def __init__(
        self,
        content: ui.Control,
        confirm: ButtonContent = DEFAULT_CONFIRM,
        confirm_style: ButtonStyleType = DEFAULT_CONFIRM_STYLE,
        cancel: ButtonContent = DEFAULT_CANCEL,
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
            self.confirm = Button(area, confirm, confirm_style)
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
            self.cancel = Button(area, cancel, cancel_style)
            self.cancel.on_click = self.on_cancel  # type: ignore
        else:
            self.cancel = None

    def dispatch(self, event: int, x: int, y: int) -> None:
        self.content.dispatch(event, x, y)
        if self.confirm is not None:
            self.confirm.dispatch(event, x, y)
        if self.cancel is not None:
            self.cancel.dispatch(event, x, y)

    def on_confirm(self) -> None:
        raise ui.Result(CONFIRMED)

    def on_cancel(self) -> None:
        raise ui.Result(CANCELLED)


class HoldToConfirm(ui.Layout):
    DEFAULT_CONFIRM = "Hold To Confirm"
    DEFAULT_CONFIRM_STYLE = ButtonConfirm
    DEFAULT_LOADER_STYLE = LoaderDefault

    def __init__(
        self,
        content: ui.Control,
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
