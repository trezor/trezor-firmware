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

from trezorlib import messages
from trezorlib.messages import FailureType
from trezorlib.tools import parse_path

XPUB_PASSPHRASE_A = "xpub6CekxGcnqnJ6osfY4Rrq7W5ogFtR54KUvz4H16XzaQuukMFZCGebEpVznfq4yFcKEmYyShwj2UKjL7CazuNSuhdkofF4mHabHkLxCMVvsqG"
XPUB_PASSPHRASE_NONE = "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy"
XPUB_CARDANO_PASSPHRASE_B = "d80e770f6dfc3edb58eaab68aa091b2c27b08a47583471e93437ac5f8baa61880c7af4938a941c084c19731e6e57a5710e6ad1196263291aea297ce0eec0f177"

ADDRESS_N = parse_path("44h/0h/0h")
XPUB_REQUEST = messages.GetPublicKey(address_n=ADDRESS_N, coin_name="Bitcoin")


def _init_session(client, session_id=None):
    """Call Initialize, check and return the session ID."""
    response = client.call(messages.Initialize(session_id=session_id))
    assert isinstance(response, messages.Features)
    assert len(response.session_id) == 32
    return response.session_id


def _get_xpub(client, passphrase=None):
    """Get XPUB and check that the appropriate passphrase flow has happened."""
    response = client.call_raw(XPUB_REQUEST)
    if passphrase is not None:
        assert isinstance(response, messages.PassphraseRequest)
        response = client.call_raw(messages.PassphraseAck(passphrase=passphrase))
    assert isinstance(response, messages.PublicKey)
    return response.xpub


@pytest.mark.skip_ui
@pytest.mark.setup_client(passphrase=True)
def test_session_with_passphrase(client):
    # Let's start the communication by calling Initialize.
    session_id = _init_session(client)

    # GetPublicKey requires passphrase and since it is not cached,
    # Trezor will prompt for it.
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASE_A

    # Call Initialize again, this time with the received session id and then call
    # GetPublicKey. The passphrase should be cached now so Trezor must
    # not ask for it again, whilst returning the same xpub.
    new_session_id = _init_session(client, session_id=session_id)
    assert new_session_id == session_id
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASE_A

    # If we set session id in Initialize to None, the cache will be cleared
    # and Trezor will ask for the passphrase again.
    new_session_id = _init_session(client)
    assert new_session_id != session_id
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASE_A

    # Unknown session id is the same as setting it to None.
    _init_session(client, session_id=b"X" * 32)
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASE_A


@pytest.mark.skip_ui
def test_session_enable_passphrase(client):
    # Let's start the communication by calling Initialize.
    session_id = _init_session(client)

    # Trezor will not prompt for passphrase because it is turned off.
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASE_NONE

    # Turn on passphrase.
    # Emit the call explicitly to avoid ClearSession done by the library function
    response = client.call(messages.ApplySettings(use_passphrase=True))
    assert isinstance(response, messages.Success)

    # The session id is unchanged, therefore we do not prompt for the passphrase.
    new_session_id = _init_session(client, session_id=session_id)
    assert session_id == new_session_id
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASE_NONE

    # We clear the session id now, so the passphrase should be asked.
    new_session_id = _init_session(client)
    assert session_id != new_session_id
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASE_A


@pytest.mark.skip_ui
@pytest.mark.setup_client(passphrase=True)
def test_clear_session_passphrase(client):
    # at first attempt, we are prompted for passphrase
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASE_A

    # now the passphrase is cached
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASE_A

    # Erase the cached passphrase
    response = client.call(messages.Initialize())
    assert isinstance(response, messages.Features)

    # we have to enter passphrase again
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASE_A


@pytest.mark.skip_ui
@pytest.mark.skip_t1
@pytest.mark.setup_client(passphrase=True)
def test_passphrase_on_device(client):
    _init_session(client)

    # try to get xpub with passphrase on host:
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PassphraseRequest)
    response = client.call_raw(messages.PassphraseAck(passphrase="A", on_device=False))
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASE_A

    # try to get xpub again, passphrase should be cached
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASE_A

    # make a new session
    _init_session(client)

    # try to get xpub with passphrase on device:
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PassphraseRequest)
    response = client.call_raw(messages.PassphraseAck(on_device=True))
    assert isinstance(response, messages.ButtonRequest)
    client.debug.input("A")
    response = client.call_raw(messages.ButtonAck())
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASE_A

    # try to get xpub again, passphrase should be cached
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASE_A


@pytest.mark.skip_ui
@pytest.mark.skip_t1
@pytest.mark.setup_client(passphrase=True)
def test_passphrase_always_on_device(client):
    # Let's start the communication by calling Initialize.
    session_id = _init_session(client)

    # Force passphrase entry on Trezor.
    response = client.call(messages.ApplySettings(passphrase_always_on_device=True))
    assert isinstance(response, messages.Success)

    # Since we enabled the always_on_device setting, Trezor will send ButtonRequests and ask for it on the device.
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.ButtonRequest)
    client.debug.input("")  # Input empty passphrase.
    response = client.call_raw(messages.ButtonAck())
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASE_NONE

    # Passphrase will not be prompted. The session id stays the same and the passphrase is cached.
    _init_session(client, session_id=session_id)
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASE_NONE

    # In case we want to add a new passphrase we need to send session_id = None.
    _init_session(client)
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.ButtonRequest)
    client.debug.input("A")  # Input empty passphrase.
    response = client.call_raw(messages.ButtonAck())
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASE_A


@pytest.mark.skip_ui
@pytest.mark.skip_t2
@pytest.mark.setup_client(passphrase=True)
def test_passphrase_on_device_not_possible_on_t1(client):
    # This setting makes no sense on T1.
    response = client.call_raw(messages.ApplySettings(passphrase_always_on_device=True))
    assert isinstance(response, messages.Failure)
    assert response.code == FailureType.DataError

    # T1 should not accept on_device request
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PassphraseRequest)
    response = client.call_raw(messages.PassphraseAck(on_device=True))
    assert isinstance(response, messages.Failure)
    assert response.code == FailureType.DataError


@pytest.mark.skip_ui
@pytest.mark.setup_client(passphrase=True)
def test_passphrase_ack_mismatch(client):
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PassphraseRequest)
    response = client.call_raw(messages.PassphraseAck(passphrase="A", on_device=True))
    assert isinstance(response, messages.Failure)
    assert response.code == FailureType.DataError


@pytest.mark.skip_ui
@pytest.mark.setup_client(passphrase=True)
def test_passphrase_missing(client):
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PassphraseRequest)
    response = client.call_raw(messages.PassphraseAck(passphrase=None))
    assert isinstance(response, messages.Failure)
    assert response.code == FailureType.DataError

    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PassphraseRequest)
    response = client.call_raw(messages.PassphraseAck(passphrase=None, on_device=False))
    assert isinstance(response, messages.Failure)
    assert response.code == FailureType.DataError


@pytest.mark.skip_ui
@pytest.mark.setup_client(passphrase=True)
def test_passphrase_length(client):
    def call(passphrase: str, expected_result: bool):
        _init_session(client)
        response = client.call_raw(XPUB_REQUEST)
        assert isinstance(response, messages.PassphraseRequest)
        response = client.call_raw(messages.PassphraseAck(passphrase))
        if expected_result:
            assert isinstance(response, messages.PublicKey)
        else:
            assert isinstance(response, messages.Failure)
            assert response.code == FailureType.DataError

    # 50 is ok
    call(passphrase="A" * 50, expected_result=True)
    # 51 is not
    call(passphrase="A" * 51, expected_result=False)
    # "š" has two bytes - 48x A and "š" should be fine (50 bytes)
    call(passphrase="A" * 48 + "š", expected_result=True)
    # "š" has two bytes - 49x A and "š" should not (51 bytes)
    call(passphrase="A" * 49 + "š", expected_result=False)


def _get_xpub_cardano(client, passphrase):
    msg = messages.CardanoGetPublicKey(address_n=parse_path("44'/1815'/0'/0/0"))
    response = client.call_raw(msg)
    if passphrase is not None:
        assert isinstance(response, messages.PassphraseRequest)
        response = client.call_raw(messages.PassphraseAck(passphrase=passphrase))
    assert isinstance(response, messages.CardanoPublicKey)
    return response.xpub


@pytest.mark.skip_ui
@pytest.mark.skip_t1
@pytest.mark.altcoin
@pytest.mark.setup_client(passphrase=True)
def test_cardano_passphrase(client):
    # Cardano uses a variation of BIP-39 so we need to ask for the passphrase again.

    session_id = _init_session(client)

    # GetPublicKey requires passphrase and since it is not cached,
    # Trezor will prompt for it.
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASE_A

    # The passphrase is now cached for non-Cardano coins.
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASE_A

    # Cardano will prompt for it again.
    assert _get_xpub_cardano(client, passphrase="B") == XPUB_CARDANO_PASSPHRASE_B

    # But now also Cardano has it cached.
    assert _get_xpub_cardano(client, passphrase=None) == XPUB_CARDANO_PASSPHRASE_B

    # And others behaviour did not change.
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASE_A

    # Initialize with the session id does not destroy the state
    _init_session(client, session_id=session_id)
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASE_A
    assert _get_xpub_cardano(client, passphrase=None) == XPUB_CARDANO_PASSPHRASE_B

    # New session will destroy the state
    _init_session(client)

    # GetPublicKey must ask for passphrase again
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASE_A

    # Cardano must also ask for passphrase again
    assert _get_xpub_cardano(client, passphrase="B") == XPUB_CARDANO_PASSPHRASE_B
