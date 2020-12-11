from trezor import ui
from trezor.ui.components.tt.text import text_center_trim_left, text_center_trim_right

if False:
    from typing import Optional


DEFAULT_ICON = "apps/webauthn/res/icon_webauthn.toif"


class ConfirmInfo:
    def __init__(self) -> None:
        self.app_icon: Optional[bytes] = None

    def get_header(self) -> str:
        raise NotImplementedError

    def app_name(self) -> str:
        raise NotImplementedError

    def account_name(self) -> Optional[str]:
        return None

    def load_icon(self, rp_id_hash: bytes) -> None:
        from trezor import res
        from . import knownapps

        fido_app = knownapps.by_rp_id_hash(rp_id_hash)
        if fido_app is not None and fido_app.icon is not None:
            self.app_icon = res.load(fido_app.icon)
        else:
            self.app_icon = res.load(DEFAULT_ICON)


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
