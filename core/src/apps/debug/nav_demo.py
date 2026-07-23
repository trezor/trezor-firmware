from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import ShowNavDemo, Success


async def nav_demo(msg: ShowNavDemo) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import show_nav_demo
    from trezor.wire import ActionCancelled

    title = "NAVIGATION DEMO"
    # (heading, body) per page. Placeholder content - easy to edit; core Python
    # is loaded at runtime so changing this needs no rebuild.
    pages = [
        (
            "Welcome",
            "This demo shows the new Trezor Safe 3 navigation. Press the RIGHT button to continue.",
        ),
        (
            "Context menu",
            "Press the LEFT button to open the context menu.",
        ),
        (
            "Go back",
            "Hold the LEFT button and press RIGHT to scroll back to the previous page.",
        ),
        # A deliberately long body so the text overflows onto another screen.
        # Overflowing text is cut with a trailing ellipsis ("...") and the
        # continuation starts with a leading ellipsis.
        (
            "Long text",
            "When a single page of text is longer than the screen can show, it "
            "flows onto the next screen. The cut is marked with an ellipsis so "
            "you always know there is more to read, and the continuation begins "
            "with an ellipsis as well. Keep pressing the right button to read on.",
        ),
        (
            "Finish",
            "Press the RIGHT button to confirm and exit the demo.",
        ),
    ]
    # (name, detail text) per context-menu item.
    menu_items = [
        ("Show info", "The context menu now works on Safe 3, just like on Safe 5 and Safe 7."),
        ("About", "Navigation demo for Trezor Safe 3 (caesar layout)."),
    ]

    try:
        await show_nav_demo(title, pages, menu_items)
    except ActionCancelled:
        return Success(message="Navigation demo cancelled")

    return Success(message="Navigation demo shown")
