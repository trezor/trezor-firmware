"""Retiring the WARD service binding, on a held confirmation.

Arrives from the WALLET host on the ordinary interface -- no daemon can bind the service channel any
more, which is why it is sent. Retiring the pin hands the role to whoever binds next, so the held
screen is the only gate.
"""

from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from trezor.messages import WardResetService, WardResetServiceAck


async def reset_service(msg: WardResetService) -> WardResetServiceAck:
    """Unbind the WARD service and retire the pin, on a held confirmation.

    Refuses while claims are unresolved -- only the service that received them can settle them --
    unless `force`, which gets its own screen naming the count. Nothing is discarded either way.
    """
    from storage import ward as storage_ward
    from trezor import wire
    from trezor.messages import WardResetServiceAck
    from trezor.ui.layouts import confirm_properties

    from . import round as sync_round
    from .keys import derive_wallet_id
    from .service import clear_binding, close_bound_channel

    if not utils.USE_WARD_SERVICE_CHANNEL:
        # Not registered in a connect build; refused here too, not by registration alone.
        raise wire.DataError("this firmware does not serve WARD over a service channel")

    if storage_ward.get_service_host_key() is None:
        raise wire.DataError("no WARD service is bound")

    unresolved = len(storage_ward.claim_list(await derive_wallet_id()))

    if unresolved and not msg.force:
        raise wire.DataError(
            "WARD: "
            + str(unresolved)
            + " queued changes are unresolved; publish them with the current service first"
        )

    # The forced path is a different decision and gets a distinctly named screen.
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

    # The channel goes first: the interface tracks one channel, so the next daemon could not bind.
    close_bound_channel("the WARD service binding was reset")
    clear_binding()
    storage_ward.clear_service_host_key()

    # The latch describes a head shared with the old daemon; the next one proves freshness anew.
    sync_round.mark_offline()

    return WardResetServiceAck(unresolved=unresolved)
