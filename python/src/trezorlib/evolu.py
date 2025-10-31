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

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def get_node(session: Session, proof: Optional[bytes]) -> bytes:
    return session.call(
        messages.EvoluGetNode(proof_of_delegated_identity=proof),
        expect=messages.EvoluNode,
    ).data


def sign_registration_request(
    session: Session, challenge: bytes, size: int, proof: bytes
) -> messages.EvoluRegistrationRequest:
    return session.call(
        messages.EvoluSignRegistrationRequest(
            challenge_from_server=challenge,
            size_to_acquire=size,
            proof_of_delegated_identity=proof,
        ),
        expect=messages.EvoluRegistrationRequest,
    )


def get_delegated_identity_key(
    session: Session,
    thp_credential: Optional[bytes] = None,
    host_static_public_key: Optional[bytes] = None,
) -> bytes:

    return session.call(
        messages.EvoluGetDelegatedIdentityKey(
            thp_credential=thp_credential,
            host_static_public_key=host_static_public_key,
        ),
        expect=messages.EvoluDelegatedIdentityKey,
    ).private_key
