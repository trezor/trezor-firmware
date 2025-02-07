from __future__ import annotations


def init_ui(
    stage: str,
    config: list[str],
    rust_features: list[str],
):

    rust_features.append("layout_caesar")

    if stage == "bootloader":
        if "bootloader_empty_lock" in config:
            rust_features.append("ui_empty_lock")
    if stage == "firmware":
        pass


def get_ui_layout() -> str:
    return "UI_LAYOUT_CAESAR"


def get_ui_layout_path() -> str:
    return "trezor/ui/layouts/caesar/"
