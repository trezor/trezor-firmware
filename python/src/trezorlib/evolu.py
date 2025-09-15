# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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


from typing import TYPE_CHECKING

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def get_evolu_node(session: "Session", proof: bytes) -> messages.EvoluNode:
    return session.call(
        messages.EvoluGetNode(proof=proof),
        expect=messages.EvoluNode,
    )


def evolu_sign_registration_request(
    session: "Session", challenge: int, size: int, proof: bytes
) -> messages.EvoluRegistrationRequest:
    return session.call(
        messages.EvoluSignRegistrationRequest(
            challenge=challenge, size=size, proof=proof
        ),
        expect=messages.EvoluRegistrationRequest,
    )


def get_delegated_identity_key(
    session: "Session",
) -> messages.EvoluDelegatedIdentityKey:
    return session.call(
        messages.EvoluGetDelegatedIdentityKey(),
        expect=messages.EvoluDelegatedIdentityKey,
    )
