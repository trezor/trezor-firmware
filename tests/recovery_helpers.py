from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent

KEYBOARD_COMPONENTS = ("MnemonicKeyboard", "Slip39Keyboard")
MAX_ATTEMPTS = 10


def layout_has_keyboard(layout: "LayoutContent") -> bool:
    components = layout.all_components()
    if any(name in components for name in KEYBOARD_COMPONENTS):
        return True
    return any(name in layout.json_str for name in KEYBOARD_COMPONENTS)


def navigate_to_keyboard(debug: "DebugLink") -> "LayoutContent":
    layout = debug.read_layout()

    for _ in range(MAX_ATTEMPTS):
        if layout_has_keyboard(layout):
            return layout
        debug.click(debug.screen_buttons.ok())
        layout = debug.read_layout()

    raise RuntimeError(
        f"Keyboard not found after {MAX_ATTEMPTS} attempts. "
        f"Expected one of: {', '.join(KEYBOARD_COMPONENTS)}"
    )
