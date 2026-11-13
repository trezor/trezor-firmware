# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import pytest

from trezorlib.firmware.sanity_struct import SanityCheckError
from trezorlib.root_packet import RootPacket, RootPacketAuth

ROOT_0 = b"\x10" * 32
ROOT_2 = b"\x12" * 32


def auth_bytes(ring_mask: int, root_rings: list[bytes]) -> bytes:
    return RootPacketAuth.SUBCON.build(
        dict(
            ring_mask=ring_mask,
            timestamp=1,
            chain_timestamp=2,
            root_rings=root_rings,
        )
    )


def packet_bytes(ring_mask: int, root_rings: list[bytes], sigmask: int = 0b11) -> bytes:
    return RootPacket.SUBCON.build(
        dict(
            auth=dict(
                ring_mask=ring_mask,
                timestamp=1,
                chain_timestamp=2,
                root_rings=root_rings,
            ),
            sigmask=sigmask,
            signature_0=b"\x00" * 2420,
            signature_1=b"\x00" * 2420,
        )
    )


def test_parse_valid() -> None:
    packet = RootPacket.parse(packet_bytes(0b101, [ROOT_0, ROOT_2]), strict=True)
    assert packet.auth.rings == {0: ROOT_0, 2: ROOT_2}


def test_auth_ring_above_max() -> None:
    with pytest.raises(SanityCheckError, match="above MAX_RINGS"):
        RootPacketAuth.parse(auth_bytes(0b1000, [ROOT_0]), strict=True)


def test_packet_ring_above_max() -> None:
    """The nested auth part is checked when parsing the whole packet."""
    with pytest.raises(SanityCheckError, match="above MAX_RINGS"):
        RootPacket.parse(packet_bytes(0b1000, [ROOT_0]), strict=True)


def test_packet_sigmask() -> None:
    with pytest.raises(SanityCheckError, match="sigmask"):
        RootPacket.parse(packet_bytes(0b1, [ROOT_0], sigmask=0b1), strict=True)
