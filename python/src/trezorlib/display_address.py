from __future__ import annotations

from typing import TYPE_CHECKING

from . import messages

if TYPE_CHECKING:
    from .debuglink import TrezorClientDebugLink as Client
    from .transport.session import Session


def show_address(
    session: "Session",
    address: str,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    case_sensitive: bool = True,
    chunkify: bool = False,
    ward_value: bytes | None = None,
    ward_proof: list[bytes] | None = None,
    ward_counter: int | None = None,
) -> str:
    session.call(
        messages.DisplayAddress(
            address=address,
            title=title,
            subtitle=subtitle,
            case_sensitive=case_sensitive,
            chunkify=chunkify,
            ward_value=ward_value,
            ward_proof=ward_proof or [],
            ward_counter=ward_counter,
        ),
        expect=messages.Success,
    )
    return address
