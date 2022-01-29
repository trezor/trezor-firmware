# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import pytest

from trezorlib import fido
from trezorlib.exceptions import Cancelled, TrezorFailure

from ...common import MNEMONIC12
from .data_webauthn import CRED1, CRED2, CRED3, CREDS

RK_CAPACITY = 100


@pytest.mark.skip_t1
@pytest.mark.altcoin
@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_add_remove(client):
    # Remove index 0 should fail.
    with pytest.raises(TrezorFailure):
        fido.remove_credential(client, 0)

    # List should be empty.
    assert fido.list_credentials(client) == []

    # Add valid credential #1.
    fido.add_credential(client, CRED1)

    # Check that the credential was added and parameters are correct.
    creds = fido.list_credentials(client)
    assert len(creds) == 1
    assert creds[0].rp_id == "example.com"
    assert creds[0].rp_name == "Example"
    assert creds[0].user_id == bytes.fromhex(
        "3082019330820138A0030201023082019330820138A003020102308201933082"
    )
    assert creds[0].user_name == "johnpsmith@example.com"
    assert creds[0].user_display_name == "John P. Smith"
    assert creds[0].creation_time == 3
    assert creds[0].hmac_secret is True

    # Add valid credential #2, which has same rpId and userId as credential #1.
    fido.add_credential(client, CRED2)

    # Check that the credential #2 replaced credential #1 and parameters are correct.
    creds = fido.list_credentials(client)
    assert len(creds) == 1
    assert creds[0].rp_id == "example.com"
    assert creds[0].rp_name is None
    assert creds[0].user_id == bytes.fromhex(
        "3082019330820138A0030201023082019330820138A003020102308201933082"
    )
    assert creds[0].user_name == "johnpsmith@example.com"
    assert creds[0].user_display_name is None
    assert creds[0].creation_time == 2
    assert creds[0].hmac_secret is True

    # Adding an invalid credential should appear as if user cancelled.
    with pytest.raises(Cancelled):
        fido.add_credential(client, CRED1[:-2])

    # Check that the invalid credential was not added.
    creds = fido.list_credentials(client)
    assert len(creds) == 1

    # Add valid credential, which has same userId as #2, but different rpId.
    fido.add_credential(client, CRED3)

    # Check that the credential was added.
    creds = fido.list_credentials(client)
    assert len(creds) == 2

    # Fill up the credential storage to maximum capacity.
    for cred in CREDS[: RK_CAPACITY - 2]:
        fido.add_credential(client, cred)

    # Adding one more valid credential to full storage should fail.
    with pytest.raises(TrezorFailure):
        fido.add_credential(client, CREDS[-1])

    # Removing the index, which is one past the end, should fail.
    with pytest.raises(TrezorFailure):
        fido.remove_credential(client, RK_CAPACITY)

    # Remove index 2.
    fido.remove_credential(client, 2)
    # Adding another valid credential should succeed now.
    fido.add_credential(client, CREDS[-1])
