import time

import pytest

from trezorlib import messages
from trezorlib.debuglink import TrezorClientDebugLink as Client

from .connect import get_encrypted_transport_protocol

pytestmark = [pytest.mark.protocol("protocol_v2"), pytest.mark.invalidate_client]


def test_abp(client: Client) -> None:
    protocol = get_encrypted_transport_protocol(client)
    msg = messages.GetFeatures()
    nonce_enc = protocol._noise.noise_protocol.cipher_state_encrypt.n

    protocol.write(0, msg)
    protocol._noise.noise_protocol.cipher_state_encrypt.n = nonce_enc
    protocol.sync_bit_send = 1 - protocol.sync_bit_send

    time.sleep(0.1)
    protocol.write(0, msg)
    time.sleep(2)

    protocol.read(0)
