from trezor import ui

from ..common.webauthn import ConfirmInfo
from .text import text_center_trim_left, text_center_trim_right


class ConfirmContent(ui.Component):
    def __init__(self, info: ConfirmInfo) -> None:
        super().__init__()
        self.info = info

    def on_render(self) -> None:
        if self.repaint:
            header = self.info.get_header()
            ui.header(header, ui.ICON_DEFAULT, ui.GREEN, ui.BG, ui.GREEN)

            if self.info.app_icon is not None:
                ui.display.image((ui.WIDTH - 64) // 2, 48, self.info.app_icon)

            app_name = self.info.app_name()
            account_name = self.info.account_name()

            # Dummy requests usually have some text as both app_name and account_name,
            # in that case show the text only once.
            if account_name is not None:
                if app_name != account_name:
                    text_center_trim_left(ui.WIDTH // 2, 140, app_name)
                    text_center_trim_right(ui.WIDTH // 2, 172, account_name)
                else:
                    text_center_trim_right(ui.WIDTH // 2, 156, account_name)
            else:
                text_center_trim_left(ui.WIDTH // 2, 156, app_name)

            self.repaint = False
