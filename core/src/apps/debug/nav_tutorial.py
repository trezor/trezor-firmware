from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import ShowNavTutorial, Success


async def nav_tutorial(msg: ShowNavTutorial) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import show_nav_tutorial
    from trezor.wire import ActionCancelled

    # Exactly seven (title, body) screens, matching the "Tutorial update"
    # design. The body texts are loaded at runtime (core Python is not frozen
    # in a debug build), so they can be tweaked without rebuilding the firmware.
    pages = [
        ("WELCOME TO TREZOR", "Learn the basics of navigating your device."),
        ("", "Use Trezor by pressing left and right buttons."),
        (
            "HOLD TO CONFIRM",
            "Hold down the right button to approve important operations.",
        ),
        (
            "MIDDLE BUTTON",
            "Press both left and right at the same time to view next screen.",
        ),
        # The "..." continuation markers at the page break are inserted
        # automatically by the layout (textual ellipsis), so they are NOT part
        # of this string - otherwise they would be doubled.
        (
            "SCREEN SCROLL",
            "Some information doesn't fit on one screen. Continue with right "
            "button. then hold left and press right to scroll up.",
        ),
        ("MENU", "Find context-specific actions and options in menu. Press left."),
        ("TUTORIAL COMPLETE", "You're ready to use your Trezor."),
    ]

    try:
        await show_nav_tutorial(pages)
    except ActionCancelled:
        return Success(message="Tutorial cancelled")

    return Success(message="Tutorial shown")
