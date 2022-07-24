from typing import Any

import storage.cache
import storage.device
from trezor import res, ui, utils


class HomescreenBase(ui.Layout):
    RENDER_INDICATOR: object | None = None

    def __init__(self) -> None:
        super().__init__()
        self.label = storage.device.get_label() or "My Trezor"
        self.repaint = storage.cache.homescreen_shown is not self.RENDER_INDICATOR

    def get_avatar(self) -> bytes:
        """Returns the image for homescreen. Is model-specific."""
        if utils.MODEL in ("T",):
            return storage.device.get_homescreen() or res.load(
                "apps/homescreen/res/bg.toif"
            )
        elif utils.MODEL in ("R",):
            # TODO: make it possible to change
            # TODO: make it a requirement of 128x64 px
            # TODO: support it for ui.display.avatar, not only ui.display.icon
            return res.load("trezor/res/model_r/homescreen.toif")  # 60*60 px
        elif utils.MODEL in ("1",):
            return res.load("trezor/res/homescreen_model_1.toif")  # 64x36 px
        else:
            raise Exception("Unknown model")

    async def __iter__(self) -> Any:
        # We need to catch the ui.Cancelled exception that kills us, because that means
        # that we will need to draw on screen again after restart.
        try:
            return await super().__iter__()
        except ui.Cancelled:
            storage.cache.homescreen_shown = None
            raise

    def on_render(self) -> None:
        if not self.repaint:
            return
        self.do_render()
        self.set_repaint(False)

    def do_render(self) -> None:
        """To be overridden by subclasses."""
        raise NotImplementedError

    def set_repaint(self, value: bool) -> None:
        self.repaint = value
        storage.cache.homescreen_shown = None if value else self.RENDER_INDICATOR

    def _before_render(self) -> None:
        if storage.cache.homescreen_shown is not self.RENDER_INDICATOR:
            super()._before_render()
