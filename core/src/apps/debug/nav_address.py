from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import NavTutorialResult, ShowNavAddress

# Milestones appended to the telemetry log, sharing the numbering used by
# `nav_tutorial.py` for begin/end so one decoder covers both flows.
_MARK_BEGIN = 1
_MARK_END_CONFIRMED = 8
_MARK_END_CANCELLED = 9
# Screens specific to this flow; the decoder names them.
_MARK_INTRO = 10
_MARK_ADDRESS = 11

_LOG_VERSION = "NAVTEL1"

# A real-looking mainnet Cardano base address, so the screen paginates and
# chunkifies exactly as it would for a genuine receive request.
_ADA_ADDRESS = (
    "addr1q9xk8gqm2m0v0m9xnfd8qpz0e9r6t4wcxk5m6dm0x8j0y6"
    "xw2s0h5r7hfa2vd9nqm7pltx0c6mxwjn5s2wh3nfz9j0qsn8xk4"
)
# `account` carries the Cardano address type, matching what the real
# `show_cardano_address` passes, and the path is a standard payment path.
_ADA_ACCOUNT = "Base"
_ADA_PATH = "m/1852'/1815'/0'/0/0"


def _encode_log() -> str:
    """Stop recording and encode the log as `NAVTEL1|<dropped>|t,code,arg;...`."""
    import trezorui_api

    events, dropped = trezorui_api.nav_telemetry_dump()
    body = ";".join(["%d,%d,%d" % ev for ev in events])
    return "%s|%d|%s" % (_LOG_VERSION, dropped, body)


async def nav_address(msg: ShowNavAddress) -> NavTutorialResult:
    import trezorui_api
    from trezor.messages import NavTutorialResult
    from trezor.ui.layouts import show_address
    from trezor.ui.layouts.common import interact
    from trezor.wire import ActionCancelled

    trezorui_api.nav_telemetry_start()
    trezorui_api.nav_telemetry_mark(_MARK_BEGIN)

    # Leaving the address screen returns to the introduction rather than ending
    # the run, so a participant can look at the address more than once. Only
    # the introduction's own ✕ ends the flow.
    while True:
        # Introduce the task, so a test participant knows what they are being
        # asked to do before the address appears.
        trezorui_api.nav_telemetry_mark(_MARK_INTRO)
        with trezorui_api.confirm_action(
            title="RECEIVE ADA",
            action=None,
            description="I will show you an ADA receive address.",
            verb="CONTINUE",
            verb_cancel="",
        ) as intro:
            result = await interact(intro, None, raise_on_cancel=None)
        if result is not trezorui_api.CONFIRMED:
            trezorui_api.nav_telemetry_mark(_MARK_END_CANCELLED)
            return NavTutorialResult(status="cancelled", log=_encode_log())

        # The genuine receive-address flow: same layout, menu and navigation a
        # real Cardano receive request would produce.
        trezorui_api.nav_telemetry_mark(_MARK_ADDRESS)
        try:
            await show_address(
                _ADA_ADDRESS,
                account=_ADA_ACCOUNT,
                path=_ADA_PATH,
                chunkify=True,
                # "Back" at the top of the address returns to the introduction.
                allow_back=True,
            )
        except ActionCancelled:
            continue  # back out of the address -> show the introduction again

        trezorui_api.nav_telemetry_mark(_MARK_END_CONFIRMED)
        return NavTutorialResult(status="shown", log=_encode_log())
