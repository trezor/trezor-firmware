from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WARDGetEntry


def _display_bytes(value: bytes) -> str:
    """Best-effort rendering of an arbitrary byte string for a trusted screen:
    UTF-8 when it decodes cleanly, otherwise hex."""
    try:
        return value.decode()
    except UnicodeError:
        from ubinascii import hexlify

        return hexlify(value).decode()


async def get_entry(msg: WARDGetEntry) -> Success:
    """WARDGetEntry handler: PULL a plaintext entry from the host and show it.

    The device holds no entries, so it asks the host for this one mid-workflow --
    WARDEntryRequest out, WARDEntryAck back -- and renders what it gets. The pull is
    the mechanism every later phase builds on; only what travels in it changes.

    FIXME(ward): the pulled value is UNAUTHENTICATED. There is no keyed path, no
    proof, no root and no encryption in this phase, so the host can return any value
    for any request and the device cannot tell. That is why the screen says
    "Unverified" -- do NOT remove that wording until the proof path lands and the
    device can actually reject a wrong answer.
    """
    from trezor.messages import Success, WARDEntryAck, WARDEntryRequest
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError, context

    app_id = msg.app_id
    identifier = msg.identifier
    if not app_id or not identifier:
        raise DataError("app_id and identifier are required")

    # The pull. Mirrors apps/webauthn/list_resident_credentials.py, which uses the
    # same primitive to ask the host for data mid-workflow.
    ack = await context.call(
        WARDEntryRequest(app_id=app_id, identifier=identifier),
        expected_type=WARDEntryAck,
    )

    # An ABSENT value means "no such entry"; a present-but-empty one is an entry whose
    # value happens to be empty. Keep those distinguishable on screen.
    props = [
        ("Domain", app_id, False),
        ("Key", _display_bytes(identifier), True),
    ]
    if ack.value is None:
        title = "Entry not found"
        props.append(("Result", "The host holds no entry for this key.", False))
    else:
        title = "Unverified entry"
        props.append(("Value", _display_bytes(ack.value), True))
    props.append(("Warning", "Not verified by this device.", False))

    await confirm_properties("ward_get_entry", title, props)

    return Success(message="WARD entry shown")
