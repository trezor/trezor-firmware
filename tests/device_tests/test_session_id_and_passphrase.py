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

import random

import pytest

from trezorlib import exceptions, messages
from trezorlib.messages import FailureType
from trezorlib.tools import parse_path

XPUB_PASSPHRASES = {
    "A": "xpub6CekxGcnqnJ6osfY4Rrq7W5ogFtR54KUvz4H16XzaQuukMFZCGebEpVznfq4yFcKEmYyShwj2UKjL7CazuNSuhdkofF4mHabHkLxCMVvsqG",
    "B": "xpub6CFxuyQpgryoR64QC38w42dLgDv5P4qWXhn1fbaN62UYzu1wJXZyrYqGnkq5d8xPUK68RXtXFBiqp3rfLGpeQ57zLtx675ZZn5ezKMAWQfu",
    "C": "xpub6BhJMNFwCjGKyRb9RUcnuHhJ2TgcnurfUrQszrmZ1rg8aadsMXLySF6LY3qf4pR7bY4vwpd1VwLPQvuCRr7BPTs8wvqrv2gexxViwj96czT",
    "D": "xpub6DK1vnTBe9EkhLACJRvovv8RSUC3MSiEV64opM7XUqrowxQ8J5C2WpA6n4vt5LS3bs618aKzi7k5w7VzNCv3SfqEeSepvvHaPhRoTvRqR5u",
    "E": "xpub6CqbQjHN7r68GHh7RsiAyrdAmyiZQgWvDxQtba2NxZHumvfMK31U6emVQSexYrTAHWQeLygRD1yXZQLsCs1LLJtaeSxMAnh2YUmP3ov6EQz",
    "F": "xpub6CRDxB1aHVNHfqjPeYhnPBhBfkQb4b4K581uYKxwv4KnkiVsRttBCXSkZM5jtP1Vv2v3wr5FxfzqWWDApLCbutBLnfwYpkWpZUmZSp6hqg5",
    "G": "xpub6DGKmAKYDF44KQEaqXY3bbJNufEDi6QPnahV4JdBxFbFCN9Vg7ZfUHxPv3uhjeeJEtPe2PjFKWRsUrEF3RDttnXf9wXq3BfYBZemwKipJ24",
    "H": "xpub6Bg8zbY94d1cBbAGT2crZL7C1UM8JWCP5CCtiHMnV4tB1pE9oCfjvZxRRFLi6EiamBDyCs3ARaHwU2FLx76YYCPFRVc1YyJi6depNtWRnoJ",
    "I": "xpub6DMpHuTZTTN64eEHcNpyeQwehXgWTrY668ZkRWnRfkFEGKpNv2uPR3js1dJgcFRksSmrdtpHqFDPTzFsR1HqvzNdgZwXmk9vCLt1ypwUzA3",
    "J": "xpub6CVeYPTG57D4tm9BvwCcakppwGJstbXyK8Yd611agusZuHmx7og3dNvr6pjMN6e4BoaNc5MZA4TjMLjMT2h2vJRU8rYLvHFUwrEL9zDbuqe",
}
XPUB_PASSPHRASE_NONE = "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy"
XPUB_CARDANO_PASSPHRASE_B = "d80e770f6dfc3edb58eaab68aa091b2c27b08a47583471e93437ac5f8baa61880c7af4938a941c084c19731e6e57a5710e6ad1196263291aea297ce0eec0f177"

ADDRESS_N = parse_path("44h/0h/0h")
XPUB_REQUEST = messages.GetPublicKey(address_n=ADDRESS_N, coin_name="Bitcoin")

SESSIONS_STORED = 10


def _init_session(client, session_id=None):
    """Call Initialize, check and return the session ID."""
    response = client.call(messages.Initialize(session_id=session_id))
    assert isinstance(response, messages.Features)
    assert len(response.session_id) == 32
    return response.session_id


def _get_xpub(client, passphrase=None):
    """Get XPUB and check that the appropriate passphrase flow has happened."""
    if passphrase is not None:
        expected_responses = [
            messages.PassphraseRequest,
            messages.ButtonRequest,
            messages.ButtonRequest,
            messages.PublicKey,
        ]
    else:
        expected_responses = [messages.PublicKey]

    with client:
        client.use_passphrase(passphrase or "")
        client.set_expected_responses(expected_responses)
        result = client.call(XPUB_REQUEST)
        return result.xpub


@pytest.mark.setup_client(passphrase=True)
def test_session_with_passphrase(client):
    # Let's start the communication by calling Initialize.
    session_id = _init_session(client)

    # GetPublicKey requires passphrase and since it is not cached,
    # Trezor will prompt for it.
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASES["A"]

    # Call Initialize again, this time with the received session id and then call
    # GetPublicKey. The passphrase should be cached now so Trezor must
    # not ask for it again, whilst returning the same xpub.
    new_session_id = _init_session(client, session_id=session_id)
    assert new_session_id == session_id
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASES["A"]

    # If we set session id in Initialize to None, the cache will be cleared
    # and Trezor will ask for the passphrase again.
    new_session_id = _init_session(client)
    assert new_session_id != session_id
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASES["A"]

    # Unknown session id is the same as setting it to None.
    _init_session(client, session_id=b"X" * 32)
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASES["A"]


@pytest.mark.setup_client(passphrase=True)
def test_multiple_sessions(client):
    # start SESSIONS_STORED sessions
    session_ids = []
    for _ in range(SESSIONS_STORED):
        session_ids.append(_init_session(client))

    # Resume each session
    for session_id in session_ids:
        new_session_id = _init_session(client, session_id)
        assert session_id == new_session_id

    # Creating a new session replaces the least-recently-used session
    _init_session(client)

    # Resuming session 1 through SESSIONS_STORED will still work
    for session_id in session_ids[1:]:
        new_session_id = _init_session(client, session_id)
        assert session_id == new_session_id

    # Resuming session 0 will not work
    new_session_id = _init_session(client, session_ids[0])
    assert new_session_id != session_ids[0]

    # New session bumped out the least-recently-used anonymous session.
    # Resuming session 1 through SESSIONS_STORED will still work
    for session_id in session_ids[1:]:
        new_session_id = _init_session(client, session_id)
        assert session_id == new_session_id

    # Creating a new session replaces session_ids[0] again
    _init_session(client)

    # Resuming all sessions one by one will in turn bump out the previous session.
    for session_id in session_ids:
        new_session_id = _init_session(client, session_id)
        assert session_id != new_session_id


@pytest.mark.setup_client(passphrase=True)
def test_multiple_passphrases(client):
    # start a session
    session_a = _init_session(client)
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASES["A"]
    # start it again wit the same session id
    new_session_id = _init_session(client, session_id=session_a)
    # session is the same
    assert new_session_id == session_a
    # passphrase is not prompted
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASES["A"]

    # start a second session
    session_b = _init_session(client)
    # new session -> new session id and passphrase prompt
    assert _get_xpub(client, passphrase="B") == XPUB_PASSPHRASES["B"]

    # provide the same session id -> must not ask for passphrase again.
    new_session_id = _init_session(client, session_id=session_b)
    assert new_session_id == session_b
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASES["B"]

    # provide the first session id -> must not ask for passphrase again and return the same result.
    new_session_id = _init_session(client, session_id=session_a)
    assert new_session_id == session_a
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASES["A"]

    # provide the second session id -> must not ask for passphrase again and return the same result.
    new_session_id = _init_session(client, session_id=session_b)
    assert new_session_id == session_b
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASES["B"]


@pytest.mark.slow
@pytest.mark.setup_client(passphrase=True)
def test_max_sessions_with_passphrases(client):
    # for the following tests, we are using as many passphrases as there are available sessions
    assert len(XPUB_PASSPHRASES) == SESSIONS_STORED

    # start as many sessions as the limit is
    session_ids = {}
    for passphrase, xpub in XPUB_PASSPHRASES.items():
        session_id = _init_session(client)
        assert session_id not in session_ids.values()
        session_ids[passphrase] = session_id
        assert _get_xpub(client, passphrase=passphrase) == xpub

    # passphrase is not prompted for the started the sessions, regardless the order
    # let's try 20 different orderings
    passphrases = list(XPUB_PASSPHRASES.keys())
    shuffling = passphrases[:]
    for _ in range(20):
        random.shuffle(shuffling)
        for passphrase in shuffling:
            session_id = _init_session(client, session_id=session_ids[passphrase])
            assert session_id == session_ids[passphrase]
            assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASES[passphrase]

    # make sure the usage order is the reverse of the creation order
    for passphrase in reversed(passphrases):
        session_id = _init_session(client, session_id=session_ids[passphrase])
        assert session_id == session_ids[passphrase]
        assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASES[passphrase]

    # creating one more session will exceed the limit
    _init_session(client)
    # new session asks for passphrase
    _get_xpub(client, passphrase="XX")

    # restoring the sessions in reverse will evict the next-up session
    for passphrase in reversed(passphrases):
        _init_session(client, session_id=session_ids[passphrase])
        _get_xpub(client, passphrase="whatever")  # passphrase is prompted


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
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASES["A"]


@pytest.mark.skip_t1
@pytest.mark.setup_client(passphrase=True)
def test_passphrase_on_device(client):
    _init_session(client)

    # try to get xpub with passphrase on host:
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PassphraseRequest)
    # using `client.call` to auto-skip subsequent ButtonRequests for "show passphrase"
    response = client.call(messages.PassphraseAck(passphrase="A", on_device=False))

    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASES["A"]

    # try to get xpub again, passphrase should be cached
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASES["A"]

    # make a new session
    _init_session(client)

    # try to get xpub with passphrase on device:
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PassphraseRequest)
    response = client.call_raw(messages.PassphraseAck(on_device=True))
    # no "show passphrase" here
    assert isinstance(response, messages.ButtonRequest)
    client.debug.input("A")
    response = client.call_raw(messages.ButtonAck())
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASES["A"]

    # try to get xpub again, passphrase should be cached
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASES["A"]


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
    client.debug.input("A")  # Input non-empty passphrase.
    response = client.call_raw(messages.ButtonAck())
    assert isinstance(response, messages.PublicKey)
    assert response.xpub == XPUB_PASSPHRASES["A"]


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


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_ack_mismatch(client):
    response = client.call_raw(XPUB_REQUEST)
    assert isinstance(response, messages.PassphraseRequest)
    response = client.call_raw(messages.PassphraseAck(passphrase="A", on_device=True))
    assert isinstance(response, messages.Failure)
    assert response.code == FailureType.DataError


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


@pytest.mark.setup_client(passphrase=True)
def test_passphrase_length(client):
    def call(passphrase: str, expected_result: bool):
        _init_session(client)
        response = client.call_raw(XPUB_REQUEST)
        assert isinstance(response, messages.PassphraseRequest)
        try:
            response = client.call(messages.PassphraseAck(passphrase=passphrase))
            assert expected_result is True, "Call should have failed"
            assert isinstance(response, messages.PublicKey)
        except exceptions.TrezorFailure as e:
            assert expected_result is False, "Call should have succeeded"
            assert e.code == FailureType.DataError

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
        response = client.call(messages.PassphraseAck(passphrase=passphrase))
    assert isinstance(response, messages.CardanoPublicKey)
    return response.xpub


@pytest.mark.skip_t1
@pytest.mark.altcoin
@pytest.mark.setup_client(passphrase=True)
def test_cardano_passphrase(client):
    # Cardano uses a variation of BIP-39 so we need to ask for the passphrase again.

    session_id = _init_session(client)

    # GetPublicKey requires passphrase and since it is not cached,
    # Trezor will prompt for it.
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASES["A"]

    # The passphrase is now cached for non-Cardano coins.
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASES["A"]

    # Cardano will prompt for it again.
    assert _get_xpub_cardano(client, passphrase="B") == XPUB_CARDANO_PASSPHRASE_B

    # But now also Cardano has it cached.
    assert _get_xpub_cardano(client, passphrase=None) == XPUB_CARDANO_PASSPHRASE_B

    # And others behaviour did not change.
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASES["A"]

    # Initialize with the session id does not destroy the state
    _init_session(client, session_id=session_id)
    assert _get_xpub(client, passphrase=None) == XPUB_PASSPHRASES["A"]
    assert _get_xpub_cardano(client, passphrase=None) == XPUB_CARDANO_PASSPHRASE_B

    # New session will destroy the state
    _init_session(client)

    # GetPublicKey must ask for passphrase again
    assert _get_xpub(client, passphrase="A") == XPUB_PASSPHRASES["A"]

    # Cardano must also ask for passphrase again
    assert _get_xpub_cardano(client, passphrase="B") == XPUB_CARDANO_PASSPHRASE_B
