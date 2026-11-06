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
    from apps.ward import service

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
        from apps.ward.caller import DISPLAY_ADDRESS, host_caller

        # The domain is the WARD service's: DisplayAddress reads the address labels the
        # host writes. A host asking for another domain is refused (shown as a warning).
        host_caller(msg.app_id, None, None)
        status, label, freshness = await ward_core.resolve_label(
            DISPLAY_ADDRESS, msg.address.encode()
        )
        log.debug(
            __name__,
            "DisplayAddress: resolve_label -> status=%s label_present=%s freshness=%d",
            status,
            label is not None,
            freshness,
        )
        # Freshness is OPTIONAL: only a host that asked the WM attaches it, and an
        # unchecked or current label is shown as it always was. A verified proof
        # against a root the WM has since moved past is still a real, but possibly
        # outdated, answer -- say so before showing it.
        if status in ("membership", "non-membership"):
            if freshness == service.FRESH_BEHIND:
                await show_warning(
                    "display_address/ward_stale",
                    "WARD label may be outdated",
                    "Your WARD entries changed since this device last synced.",
                )
            elif freshness == service.FRESH_INVALID:
                await show_warning(
                    "display_address/ward_stale",
                    "WARD label not confirmed",
                    "The WARD Manager's freshness attestation did not verify.",
                )
        # "cached": the host could not serve a proof and a STICKY cached copy is shown
        # unverified -- the title says so (see service.cached_label).
        if status in ("membership", "cached"):
            label_text = (
                service.display_text(bytes(label)) if label is not None else None
            )
            if label is not None and label_text is None:
                # The subtitle carries no field name to mark a hex form, so a label that is
                # not plain text is not shown at all rather than shown ambiguously.
                await show_warning(
                    "display_address/ward_label_not_text",
                    "WARD label not shown",
                    "The verified label is not plain text.",
                )
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
