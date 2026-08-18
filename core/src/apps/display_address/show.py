"""Show an address on a trusted screen, labelled from WARD.

The app that demonstrates what WARD is FOR. Everything else in `apps.ward` is the host
driving WARD; this is firmware consuming it -- the same shape a Bitcoin or Ethereum
"receive address" screen would take once it adopts `apps.ward.label`, which is why the
lookup lives there and only the screen lives here.

TWO THINGS THE HOST DOES NOT GET TO DECIDE. It cannot supply the label -- there is no wire
field for one -- and it cannot suppress the address by breaking the lookup. Both follow from
the same reading: the label is a claim about WHO an address belongs to, made on the very
screen the user is checking that against, so it may come only from a source the device can
name, and it may never become a reason not to show the address itself.

WHY THE LABEL GETS ITS OWN SCREEN rather than riding along as the address screen's subtitle.
Of the three layouts, only Eckhart renders `show_address`'s `subtitle` and `warning`; Bolt
drops both and Delizia passes `subtitle=None, hint=None` into its flow. Passing the label
there and calling it done would show it on one device in three and silently omit it -- and
the provenance line with it -- on the others, which for a feature whose entire content is
"this address is called X, and here is how well I know that" is the worst available failure.
So the label and its provenance go through `confirm_properties`, which every layout renders,
and the address then follows on the real address screen with its QR and its chunking. The
subtitle and warning are still passed to it, so Eckhart repeats them inline; the FIXME below
is the layout work that would let this collapse back into one screen.

FIXME(ward): fold these two screens into one once `show_address` renders `subtitle` and
`warning` on every layout. That is a change in the Rust UI layer, not here.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DisplayAddress, Success

# What this module is, when it asks WARD for a label. A CONSTANT -- never `msg.app_id` --
# because it is the identity of the caller, and a caller that took its own identity from the
# request would be letting the request choose its own permissions. The domain being read is
# the separate, host-named argument below.
_PRINCIPAL = "display_address"


async def show(msg: DisplayAddress) -> Success:
    from trezor import log
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties, show_address
    from trezor.wire import DataError

    from apps.ward.common import display_bytes
    from apps.ward.label import resolve_label

    if not msg.address:
        # The one thing worth refusing over: with no address there is nothing to show, and
        # a screen displaying an empty string is worse than an error.
        raise DataError("address is required")

    label: bytes | None = None
    try:
        label, note = await resolve_label(
            _PRINCIPAL, msg.address.encode(), domain=msg.app_id
        )
    except Exception as e:
        # DELIBERATELY BROAD, and it does not re-raise. Everything reachable here is a
        # failure to LABEL -- a host that cannot answer the pull, an ack that does not
        # verify, an uninitialised device -- and none of it says anything about the address,
        # which is what the user asked to see. So the address is shown with the failure
        # named next to it rather than replaced by a Failure the user never sees.
        log.warning(__name__, "label lookup failed (%s): %s", type(e).__name__, e)
        note = "Label unavailable."

    label_text = display_bytes(label) if label is not None else None

    # "No label" is stated, never left to be inferred. A user who does not know that a label
    # WOULD have appeared cannot read its absence as anything at all, so the one case that
    # must not be silent is the one with nothing to show.
    if label_text is None:
        shown = "None"
    elif label_text == "":
        # A label the user deliberately BLANKED is an entry that exists, and WARD keeps it
        # distinct from one that does not. Rendering it as an empty line would collapse the
        # two on the only surface where the difference is visible.
        shown = "(empty)"
    else:
        shown = label_text

    await confirm_properties(
        "display_address_label",
        "Address label",
        [("Label", shown, False), ("Source", note, False)],
    )

    # The host's `subtitle` fills the slot ONLY when no label resolved. A resolved label is
    # the whole point of the screen and outranks anything the host wanted to put there; a
    # host-chosen subtitle sitting beside a device-resolved label would be two claims about
    # the same address with nothing on screen to tell them apart.
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
