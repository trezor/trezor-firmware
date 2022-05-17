from typing import Sequence

from trezor import ui
from trezor.ui.constants import QR_SIDE_MAX

_QR_WIDTHS = (21, 25, 29, 33, 37, 41, 45, 49, 53, 57)
_THRESHOLDS_BINARY = (14, 26, 42, 62, 84, 106, 122, 152, 180, 213)
_THRESHOLDS_ALPHANUM = (20, 38, 61, 90, 122, 154, 178, 221, 262, 311)


def _qr_version_index(data: str, thresholds: Sequence[int]) -> int:
    for i, threshold in enumerate(thresholds):
        if len(data) <= threshold:
            return i
    raise ValueError  # data too long


def is_alphanum_only(data: str) -> bool:
    return all(c in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $*+-./:" for c in data)


class Qr(ui.Component):
    def __init__(self, data: str, case_sensitive: bool, x: int, y: int) -> None:
        super().__init__()
        if case_sensitive and not is_alphanum_only(data):
            # must encode in BINARY mode
            version_idx = _qr_version_index(data, _THRESHOLDS_BINARY)
        else:
            # can make the QR code more readable by using the best version
            version_idx = _qr_version_index(data, _THRESHOLDS_ALPHANUM)
            if len(data) > _THRESHOLDS_BINARY[version_idx]:
                data = data.upper()

        size = _QR_WIDTHS[version_idx]

        self.data = data
        self.x = x
        self.y = y
        self.scale = QR_SIDE_MAX // size

    def on_render(self) -> None:
        if self.repaint:
            ui.display.qrcode(self.x, self.y, self.data, self.scale)
            self.repaint = False
