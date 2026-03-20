from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


def layout_has_component(
    layout: "LayoutContent",
    component_names: Sequence[str],
    *,
    check_json: bool = False,
) -> bool:
    components = layout.all_components()
    if any(name in components for name in component_names):
        return True

    if check_json:
        return any(name in layout.json_str for name in component_names)

    return False


def navigate_to_keyboard(
    debug: "DebugLink",
    *,
    component_names: Sequence[str],
    max_attempts: int = 10,
    check_json: bool = False,
) -> "LayoutContent":
    layout = debug.read_layout()

    for _ in range(max_attempts):
        if layout_has_component(layout, component_names, check_json=check_json):
            return layout
        debug.click(debug.screen_buttons.ok())
        layout = debug.read_layout()

    component_list = ", ".join(component_names)
    raise RuntimeError(
        f"Keyboard not found after {max_attempts} attempts. Expected one of: {component_list}"
    )