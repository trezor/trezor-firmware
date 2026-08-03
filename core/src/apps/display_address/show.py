from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DisplayAddress, Success


async def show(msg: "DisplayAddress") -> "Success":
    """PULL: the device requests the WARD proof on demand (WARDProofRequest), the
    host answers (WARDProofAck), and the label is verified against the device's
    authenticated WARD root. The PUSH variant is apps.display_address.show_with_proof.
    """
    from trezor import log
    from trezor.messages import Success
    from trezor.ui.layouts import show_address, show_warning

    from apps.common import ward as ward_core

    log.debug(
        __name__,
        "DisplayAddress: address=%s app_id=%s case_sensitive=%s",
        msg.address,
        msg.app_id,
        msg.case_sensitive,
    )

    label_text: str | None = None
    status = "unverified"
    try:
        # Principal "display_address" (capability); the queried domain comes from the
        # request (msg.app_id) so the display can show a label written by any app.
        status, label = await ward_core.resolve_label(
            "display_address", msg.address.encode(), domain=msg.app_id
        )
        log.debug(
            __name__,
            "DisplayAddress: resolve_label -> status=%s label_present=%s",
            status,
            label is not None,
        )
        if status == "membership":
            label_text = bytes(label).decode() if label is not None else None
        # status == "unknown" (a proof was supplied but did not verify) and
        # "non-membership" both fall through to show the address with `status` as the
        # title and NO label. A wrong/stale proof therefore renders as "unknown" (never
        # as a verified label — the host cannot forge one), so no extra warning screen
        # is needed here; the title itself surfaces that the label is unverified.
    except Exception as e:
        # The label could not be RESOLVED at all (malformed/empty WARDProofAck, a host
        # DB out of sync with the device's root, or any wire/verify failure). NEVER
        # abort with a bare Failure and no screen: surface it ON-DEVICE, log it, and
        # still show the address without a verified label. Broad by design — showing
        # *something* always beats a blank/aborted flow (the user's requirement).
        log.warning(
            __name__,
            "DisplayAddress: label resolution failed (%s): %s",
            type(e).__name__,
            e,
        )
        await show_warning(
            "display_address/ward_error",
            "WARD label unavailable",
            str(e) or "The label proof could not be provided or verified.",
        )
        status = "unverified"

    log.debug(__name__, "DisplayAddress: showing address, title=%s", status)
    await show_address(
        msg.address,
        title=status,
        subtitle=label_text,
        case_sensitive=bool(msg.case_sensitive),
        chunkify=bool(msg.chunkify),
        br_name="display_address/show",
    )

    return Success(message="Address shown")
