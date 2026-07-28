from __future__ import annotations

from typing import TYPE_CHECKING

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def show_address(
    session: "Session",
    address: str,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    case_sensitive: bool = True,
    chunkify: bool = False,
) -> str:
    """Display an address with a PULL-authenticated WARD label: the device requests
    the proof on demand (WARDProofRequest), answered by the registered
    ``ward_proof_callback``. Register a callback before calling."""
    session.call(
        messages.DisplayAddress(
            address=address,
            title=title,
            subtitle=subtitle,
            case_sensitive=case_sensitive,
            chunkify=chunkify,
        ),
        expect=messages.Success,
    )
    return address


def show_address_with_proof(
    session: "Session",
    address: str,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    case_sensitive: bool = True,
    chunkify: bool = False,
    value: bytes | None = None,
    proof: list[bytes] | None = None,
    counter: int | None = None,
    witness_address: bytes | None = None,
    witness_value: bytes | None = None,
    witness_counter: int | None = None,
) -> str:
    """Display an address with a PUSH-authenticated WARD label: the host attaches the
    proof up-front (membership: value/counter; non-membership: witness_*)."""
    session.call(
        messages.DisplayAddressWithProof(
            address=address,
            title=title,
            subtitle=subtitle,
            case_sensitive=case_sensitive,
            chunkify=chunkify,
            value=value,
            proof=proof or [],
            counter=counter,
            witness_address=witness_address,
            witness_value=witness_value,
            witness_counter=witness_counter,
        ),
        expect=messages.Success,
    )
    return address
