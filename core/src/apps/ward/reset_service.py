"""Retiring the WARD service binding: an ownership migration with a user decision in it.

A HANDLER OF ITS OWN because it is the one WARD message on a service build that does not use the
service channel, and the only one whose subject is the BINDING rather than the replica. Every other
exchange in `service.py` is device-to-daemon; this one cannot be, since the reason to send it is
that no daemon can bind that channel any more. So it arrives from the WALLET host, on the ordinary
interface, and the receive boundary on the service interface refuses it there -- correctly, because
a party able to reach it over the service channel would already hold the role.

AN OWNERSHIP MIGRATION, NOT A CREDENTIAL RESET, and the distinction decides the whole shape. A
credential reset would be "prove you are the owner, get a new key"; there is no new key here and
nobody to prove anything to. Retiring the pin hands the role to WHOEVER BINDS NEXT -- so the only
thing between a paired host and the WARD service role is the screen, which is why it holds, and why
the request's own authentication ("some paired host") is treated as saying nothing.
"""

from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from trezor.messages import WardResetService, WardResetServiceAck


async def reset_service(msg: WardResetService) -> WardResetServiceAck:
    """Unbind the WARD service and retire the pin, on a held confirmation.

    UNRESOLVED CLAIMS ARE THE GATE, and they are a real obstacle rather than a caution. A claim is a
    queued change that was handed to the service and whose fate is not yet known; the only party
    that can settle it is the service that received it, because settling means folding the
    transitions around it out of that service's history. A fresh daemon serves a wallet at genesis
    and has no history to fold -- so a reset performed over an open claim does not merely delay the
    answer, it removes the last party able to give one.

    So the ordinary path refuses and says how many are outstanding, which is actionable: reconnect
    the current service and drain them. `force` is for the case the refusal cannot help with -- the
    daemon is gone for good -- and it gets a screen naming the count rather than a quieter one,
    because "some number of changes you approved may or may not exist" is the actual consequence.

    NOTHING IS DISCARDED EITHER WAY. The claims stay, the queued records stay PENDING, every root
    stays. That leaves the wallet recoverable if the daemon ever comes back, and it follows the rule
    the rest of this subsystem keeps: nothing erases a record except the user saying so, and the user
    was asked about the BINDING here, not about their data.
    """
    from storage import ward as storage_ward
    from trezor import wire
    from trezor.messages import WardResetServiceAck
    from trezor.ui.layouts import confirm_properties

    from . import round as sync_round
    from .keys import derive_wallet_id
    from .service import clear_binding, close_bound_channel

    if not utils.USE_WARD_SERVICE_CHANNEL:
        # Unreachable in a connect build, where this is not registered. Stated so the refusal does
        # not rest on registration alone.
        raise wire.DataError("this firmware does not serve WARD over a service channel")

    if storage_ward.get_service_host_key() is None:
        # Nothing to migrate. Reported rather than treated as success, because a host that gets an
        # ack here would conclude a binding it never saw has been cleared.
        raise wire.DataError("no WARD service is bound")

    unresolved = len(storage_ward.claim_list(await derive_wallet_id()))

    if unresolved and not msg.force:
        raise wire.DataError(
            "WARD: "
            + str(unresolved)
            + " queued changes are unresolved; publish them with the current service first"
        )

    # A DISTINCT SCREEN FOR THE DESTRUCTIVE PATH, named distinctly, because the two are not the same
    # decision: one gives up a binding, the other gives up knowing what happened to changes the user
    # already approved. Held either way -- the request is authenticated only as "some paired host".
    props = [("Action", "Forget the bound WARD service", False)]
    br_name = "ward_reset_service"
    if unresolved:
        br_name = "ward_reset_service_force"
        props.append(("Unresolved changes", str(unresolved), False))
        props.append(
            (
                "Warning",
                "This device cannot tell whether these were published, and a new service cannot find out.",
                False,
            )
        )

    await confirm_properties(br_name, "Reset WARD service", props, hold=True)

    # THE CHANNEL GOES FIRST, and it has to: the interface tracks one channel at a time, so leaving
    # the old daemon's in place would meet the next one with a busy interface rather than a bind --
    # the pin retired and the role still unreachable.
    close_bound_channel("the WARD service binding was reset")
    clear_binding()
    storage_ward.clear_service_host_key()

    # The latch is about a head shared with the daemon that is no longer bound, so it cannot survive
    # it -- the same reasoning `end_pairing_and_replace` gives for not migrating a service session
    # across a reconnection. The next service proves freshness from scratch.
    sync_round.mark_offline()

    return WardResetServiceAck(unresolved=unresolved)
