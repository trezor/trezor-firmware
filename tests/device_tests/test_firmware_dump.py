from hashlib import blake2s

from trezorlib import firmware
from trezorlib.debuglink import TrezorClientDebugLink as Client

FIRMWARE_LENGTHS = {
    "1": 7 * 128 * 1024 + 64 * 1024,
    "T": 13 * 128 * 1024,
}


def test_firmware_dump_hash(client: Client) -> None:
    data = firmware.get_firmware(client)
    assert len(data) == FIRMWARE_LENGTHS[client.features.model]

    if client.features.fw_vendor != "EMULATOR":
        # check that the dumped data is not empty
        assert not all(byte == 0xFF for byte in data)

    expected_hash = blake2s(data).digest()
    hash = firmware.get_hash(client, None)
    assert hash == expected_hash

    challenge = b"Hello Trezor"
    expected_hash = blake2s(data, key=challenge).digest()
    hash = firmware.get_hash(client, challenge)
    assert hash == expected_hash
