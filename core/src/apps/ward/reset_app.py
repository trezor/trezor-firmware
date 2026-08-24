"""Retiring the pinned WARD app: an ownership migration, with a user decision in it.

THE ONE WARD REQUEST THAT DOES NOT REQUIRE THE WARD ROLE, and it cannot: the reason to send it is
that the app holding the role cannot ask -- its key is gone with its installation, or the user has
moved to a different app. Requiring the role to retire the pin would make the pin unrecoverable,
which is the single property it must not have. So it is left out of `app_role`'s message list on
purpose, and the omission is part of the design rather than an oversight (see the note there).

THE SCREEN IS THEREFORE THE ONLY GATE. This request authenticates its sender as "some paired host",
which is exactly the granularity the pin exists to improve on, so it is treated as saying nothing at
all -- and what stands between any paired host and the WARD role is a held confirmation in front of
the user. The daemon's pin is recovered by the same argument in `reset_service`, and the two are
deliberately the same shape.

NOTHING IS DISCARDED. Not an entry, not a queued change, not a claim, not a root. The pin says WHO
may operate WARD; forgetting that is not a reason to throw away what the user stored, and the rule
this subsystem keeps is that nothing erases a record except the user saying so -- the user was asked
about the role here, not about their data.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardResetApp, WardResetAppAck


async def reset_app(msg: WardResetApp) -> WardResetAppAck:
    """Retire the app pin on a held confirmation, and report whether there was one."""
    from storage import ward as storage_ward
    from trezor.messages import WardResetAppAck
    from trezor.ui.layouts import confirm_properties

    # READ BEFORE THE SCREEN, so what is reported is the state the user was asked about rather than
    # the state after a race with anything else that might have cleared it.
    was_bound = storage_ward.get_app_host_key() is not None

    # A SCREEN EITHER WAY, and it is held either way. An unbound device is not a special case worth a
    # quieter path: the outcome the user is agreeing to is the same -- the next app that asks gets the
    # role -- and a request that silently succeeded when nothing was bound would be a way to find out
    # whether anything is bound without the user seeing anything.
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

    # UNCONDITIONAL, even when nothing was bound: `clear` on an absent key is the same no-op the
    # storage layer promises, and branching here would only add a path that does nothing differently.
    storage_ward.clear_app_host_key()

    return WardResetAppAck(was_bound=was_bound)
