from __future__ import annotations


def init_ui(
    stage: str,
    config: list[str],
    rust_features: list[str],
):

    rust_features.append("layout_bolt")

    if stage == "firmware":
        rust_features.append("ui_blurring")
        rust_features.append("ui_jpeg")


def get_ui_layout() -> str:
    return "UI_LAYOUT_BOLT"


def get_ui_layout_path() -> str:
    return "trezor/ui/layouts/bolt/"
