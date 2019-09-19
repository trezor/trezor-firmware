from trezor import log, ui
from trezor.ui.text import text_center_trim_left, text_center_trim_right

if False:
    from typing import Optional


class ConfirmInfo:
    def __init__(self) -> None:
        self.app_icon = None  # type: Optional[bytes]

    def get_header(self) -> str:
        raise NotImplementedError

    def app_name(self) -> str:
        raise NotImplementedError

    def account_name(self) -> Optional[str]:
        return None

    def load_icon(self, rp_id_hash: bytes) -> None:
        from trezor import res
        from apps.webauthn.knownapps import knownapps

        try:
            namepart = knownapps[rp_id_hash]["label"].lower().replace(" ", "_")
            icon = res.load("apps/webauthn/res/icon_%s.toif" % namepart)
        except Exception as e:
            icon = res.load("apps/webauthn/res/icon_webauthn.toif")
            if __debug__:
                log.exception(__name__, e)
        self.app_icon = icon


class ConfirmContent(ui.Component):
    def __init__(self, info: ConfirmInfo) -> None:
        self.info = info
        self.repaint = True

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
