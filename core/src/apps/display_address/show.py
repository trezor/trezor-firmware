"""Show an address on a trusted screen, labelled from WARD.

The host cannot supply the label (there is no wire field for one) and cannot suppress the address
by breaking the lookup. The label gets its own `confirm_properties` screen because only Eckhart
renders `show_address`'s `subtitle` and `warning`.

FIXME(ward): fold the two screens into one once `show_address` renders `subtitle` and `warning` on
every layout.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DisplayAddress, Success

# The caller's identity, never `msg.app_id`: a request must not choose its own permissions.
_PRINCIPAL = "display_address"


async def show(msg: DisplayAddress) -> Success:
    from trezor import log
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties, show_address
    from trezor.wire import DataError

    from apps.ward.common import display_bytes
    from apps.ward.label import resolve_label

    if not msg.address:
        raise DataError("address is required")

    label: bytes | None = None
    try:
        label, note = await resolve_label(
            _PRINCIPAL, msg.address.encode(), domain=msg.app_id
        )
    except Exception as e:
        # Deliberately broad: a failure to LABEL says nothing about the address the user asked to see.
        log.warning(__name__, "label lookup failed (%s): %s", type(e).__name__, e)
        note = "Label unavailable."

    label_text = display_bytes(label) if label is not None else None
    # "No label" is stated, and a deliberately blank label stays distinct from a missing one.
    if label_text is None:
        shown = "None"
    else:
        shown = label_text or "(empty)"

    await confirm_properties(
        "display_address_label",
        "Address label",
        [("Label", shown, False), ("Source", note, False)],
    )

    # The host's subtitle only when no label resolved: two claims about one address would be
    # indistinguishable on screen.
    await show_address(
        msg.address,
        title=msg.title,
        subtitle=label_text if label_text is not None else msg.subtitle,
        warning=note,
        case_sensitive=bool(msg.case_sensitive),
        chunkify=bool(msg.chunkify),
        br_name="display_address",
    )

    return Success(message="Address shown")
