from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DisplayAddress, Success


async def show(msg: "DisplayAddress") -> "Success":
    """PULL: the device requests the WARD proof on demand (WARDProofRequest), the
    host answers (WARDProofAck), and the label is verified against the device's
    authenticated WARD root. The PUSH variant is apps.display_address.show_with_proof.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import show_address, show_warning
    from trezor.wire import DataError

    from apps.common import ward as ward_core

    label_text: str | None = None
    try:
        # Principal "display_address" (capability); the queried domain comes from the
        # request (msg.app_id) so the display can show a label written by any app.
        status, label = await ward_core.resolve_label(
            "display_address", msg.address.encode(), domain=msg.app_id
        )
    except DataError as e:
        # The label could not be RESOLVED at all: the host could not supply a proof
        # the device can check (e.g. an empty/malformed WARDProofAck, or a host DB out
        # of sync with the device's authenticated root). Surface it ON-DEVICE instead
        # of aborting with a bare Failure and no screen, then still show the address
        # without a verified label.
        await show_warning(
            "display_address/ward_error",
            "WARD label unavailable",
            str(e) or "The label proof could not be provided or verified.",
        )
        status = "unverified"
    else:
        if status == "membership":
            label_text = bytes(label).decode() if label is not None else None
        elif status == "unknown":
            # A proof WAS supplied but did not verify against the device's authenticated
            # root — distinct from a proven non-membership. Warn on-device so a bad/stale
            # proof is never silently rendered as a plain address.
            await show_warning(
                "display_address/ward_error",
                "WARD label could not be verified",
                "The proof did not match the device's authenticated root.",
            )

    await show_address(
        msg.address,
        title=status,
        subtitle=label_text,
        case_sensitive=bool(msg.case_sensitive),
        chunkify=bool(msg.chunkify),
        br_name="display_address/show",
    )

    return Success(message="Address shown")
