from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import NavTutorialResult, ShowNavTutorial

# Milestones appended to the telemetry log; the menu-related codes live in
# `trezor.ui.layouts.caesar`. Decoded by `trezorlib.nav_telemetry`.
_MARK_BEGIN = 1
_MARK_END_CONFIRMED = 8
_MARK_END_CANCELLED = 9

# Format tag of the encoded log, so the decoder can reject foreign payloads.
_LOG_VERSION = "NAVTEL1"


def _encode_log() -> str:
    """Stop recording and encode the log as `NAVTEL1|<dropped>|t,code,arg;...`."""
    import trezorui_api

    events, dropped = trezorui_api.nav_telemetry_dump()
    body = ";".join(["%d,%d,%d" % ev for ev in events])
    return "%s|%d|%s" % (_LOG_VERSION, dropped, body)


async def nav_tutorial(msg: ShowNavTutorial) -> NavTutorialResult:
    import trezorui_api
    from trezor.messages import NavTutorialResult
    from trezor.ui.layouts import show_nav_tutorial
    from trezor.wire import ActionCancelled

    # Exactly eight screens, matching the "Tutorial update" design (v2). The
    # texts are loaded at runtime (core Python is not frozen in a debug build),
    # so they can be tweaked without rebuilding the firmware.
    #
    # A screen is `(title, body)`, optionally extended with `scrolled_title`
    # and `scrolled_body` - what the *second* sub-page shows. Supplying both
    # lets the scroll exercise say something different once scrolled, instead
    # of merely continuing the first sentence.
    pages = [
        ("WELCOME TO TREZOR", "Learn the basics of navigating your device."),
        ("", "Use Trezor by pressing LEFT and RIGHT buttons."),
        (
            "HOLD TO CONFIRM",
            "Hold down the RIGHT button to approve important operations.",
        ),
        (
            "MIDDLE BUTTON",
            "Press both LEFT and RIGHT at the same time to view next screen.",
        ),
        # The Shift exercise (figma 426:1693 / 426:1720). On the second
        # sub-page the right button is a dead end, so the only way onwards is
        # holding LEFT and pressing RIGHT.
        (
            "TRY SCROLLING",
            "Press RIGHT to view next screen.",
            "GO BACK",
            "Hold LEFT, press RIGHT.",
        ),
        # Reached only by performing the gesture (figma 456:2899).
        ("REMEMBER", "Hold LEFT and press RIGHT to scroll up."),
        ("MENU", "Find context-specific actions and options in menu. Press LEFT."),
        ("TUTORIAL COMPLETE", "You're ready to use your Trezor."),
    ]

    # Record every interaction so the walkthrough can be analysed afterwards.
    trezorui_api.nav_telemetry_start()
    trezorui_api.nav_telemetry_mark(_MARK_BEGIN)

    try:
        await show_nav_tutorial(pages)
    except ActionCancelled:
        trezorui_api.nav_telemetry_mark(_MARK_END_CANCELLED)
        return NavTutorialResult(status="cancelled", log=_encode_log())

    trezorui_api.nav_telemetry_mark(_MARK_END_CONFIRMED)
    return NavTutorialResult(status="shown", log=_encode_log())
