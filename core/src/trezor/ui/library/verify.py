"""The person's own address or key, checked against the host.

These two screens are core's own flows, not a set of facts: the value, its QR
code, the account and path, the "does not match" loop and the "confirmed" message
are all drawn by the model's `flow_get_address` and `flow_get_pubkey`. So this is
the one place the driver uses the stage-A layout calls rather than the new field
kinds: a single value has no fields to carry, and the flow around it is already the
same one core's own apps use.

WIP: `flow_get_address` and `flow_get_pubkey` are `NotImplementedError` on Bolt
and Caesar (`layout_bolt/ui_firmware.rs`, `layout_caesar/ui_firmware.rs`), so
neither screen runs there. The pinned stage-A exception is
`trezor.ui.layouts.show_address` / `show_pubkey`, which do work on all four
models.
"""

import trezorui_api
from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import raise_if_not_confirmed

from . import success


async def address(
    name: str,
    value: str,
    account: str | None,
    path: str | None,
) -> None:
    """Show the address and wait until the person confirms it matches."""
    with trezorui_api.flow_get_address(
        address=value,
        title=TR.words__receive,
        subtitle=None,
        description="",
        hint=None,
        chunkify=True,
        address_qr=value,
        case_sensitive=True,
        account=account,
        path=path,
        xpubs=[],
        br_name=name,
        br_code=ButtonRequestType.Address,
    ) as layout:
        await raise_if_not_confirmed(layout, br_name=None)

    await success.show(None, TR.address__confirmed)


async def pubkey(
    name: str,
    value: str,
    account: str | None,
    path: str | None,
) -> None:
    """Show the public key and wait until the person confirms it matches."""
    with trezorui_api.flow_get_pubkey(
        pubkey=value,
        title=TR.address__public_key,
        subtitle=None,
        description=None,
        hint=None,
        chunkify=False,
        pubkey_qr=value,
        case_sensitive=True,
        account=account,
        path=path,
        br_name=name,
        br_code=ButtonRequestType.PublicKey,
    ) as layout:
        await raise_if_not_confirmed(layout, br_name=None)

    await success.show(None, TR.address__public_key_confirmed)
