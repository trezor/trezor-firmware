"""Retiring the pinned WARD app, on a held confirmation.

Deliberately NOT gated by the WARD role -- the app holding it may be gone -- so the held screen is
the only gate. Nothing is discarded: the pin says who may operate WARD, not what is stored.
Same shape as `reset_service`.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardResetApp, WardResetAppAck


async def reset_app(msg: WardResetApp) -> WardResetAppAck:
    """Retire the app pin on a held confirmation, and report whether there was one."""
    from storage import ward as storage_ward
    from trezor.messages import WardResetAppAck
    from trezor.ui.layouts import confirm_properties

    # Read before the screen: report the state the user was asked about.
    was_bound = storage_ward.get_app_host_key() is not None

    # A held screen even when unbound, so the request cannot silently probe whether a pin exists.
    props = [("Action", "Forget the app that may use WARD", False)]
    if was_bound:
        props.append(
            (
                "Effect",
                "The application using WARD now will be refused. The next one to ask takes over.",
                False,
            )
        )
    else:
        props.append(("Note", "No application holds this yet.", False))
    props.append(("Kept", "Every entry, queued change and root stays.", False))

    await confirm_properties("ward_reset_app", "Reset WARD app", props, hold=True)

    storage_ward.clear_app_host_key()

    return WardResetAppAck(was_bound=was_bound)
