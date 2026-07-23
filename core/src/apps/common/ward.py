"""Core WARD-facing API: the internal platform boundary (TC) between on-device
Trezor apps and the WARD trust anchor (TW).

On-device apps (Bitcoin/Ethereum getAddress, signing flows, ...) must not call
the WARD domain directly; they go through this module, which enforces an
`app_id` capability check before routing the request to `apps.ward`. This is the
`Trezor App -> Core(appId) -> WARD` path: the host protobuf handlers
(apps.authdb / apps.ward.*) are a separate, wire-facing entry point.

Capabilities are a static allowlist keyed by the first-party app id. Apps are
firmware modules, so `app_id` is a trusted constant the caller passes -- the
boundary's job is capability scoping (which app may do what), not authenticating
an untrusted principal.
"""

from typing import TYPE_CHECKING

# Capability allowlist. Each app id maps to the WARD capabilities it may invoke.
_CAPABILITIES = {
    "bitcoin": ("lookup",),
    "ethereum": ("lookup",),
}

if TYPE_CHECKING:
    pass


def _authorize(app_id: str, capability: str) -> None:
    from trezor.wire import DataError

    if capability not in _CAPABILITIES.get(app_id, ()):
        raise DataError("app not authorized for WARD " + capability)


async def lookup_label(
    app_id: str,
    address: bytes,
    value: bytes,
    proof: list[bytes],
    counter: int,
) -> bytes | None:
    """Authorize `app_id` for `lookup`, then authenticate (address, value)
    against the device's WARD root. Returns the verified label, or None if the
    proof does not verify (or the tree is empty). Raises DataError if `app_id`
    lacks the capability.
    """
    _authorize(app_id, "lookup")
    from apps.ward import ward_lookup

    return await ward_lookup(address, value, proof, counter)


async def set_entry(app_id: str, *args, **kwargs):
    """Capability-gated entry point for on-device edits (API parity with the
    diagram's Core surface). Gated on the `set_entry` capability; no first-party
    app is granted it yet, so this raises until a caller and its capability are
    added to `_CAPABILITIES`.
    """
    _authorize(app_id, "set_entry")
    raise NotImplementedError  # no on-device set_entry caller wired yet
