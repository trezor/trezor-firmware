import pytest

from trezorlib import messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.mapping import DEFAULT_MAPPING
from trezorlib.transport import Transport
from trezorlib.transport.thp.protocol_v1 import ProtocolV1Channel

pytestmark = [
    pytest.mark.protocol("protocol_v2"),
    pytest.mark.invalidate_client,
    pytest.mark.setup_client(uninitialized=True),
]


def write_padded(transport: Transport, msg: bytes):
    padded = msg.ljust(transport.CHUNK_SIZE, b"\x00")
    transport.write_chunk(padded)


def test_v1(client: Client):
    protocol_v1 = ProtocolV1Channel(client.protocol.transport, DEFAULT_MAPPING)
    transport = protocol_v1.transport

    # There should be a failure response to received init packet (starts with "?##")
    write_padded(transport, b"?## Init packet")
    res = protocol_v1.read()
    assert res == messages.Failure(code=messages.FailureType.InvalidProtocol)

    # There should be no response for continuation packet (starts with "?" only)
    write_padded(transport, b"? Cont packet")


def test_v2_unallocated(client: Client):
    transport = client.protocol.transport

    # A message to unallocated THP channel 0x789a should result in an error
    write_padded(transport, bytes.fromhex("04789a000c001122334455667796643c6c"))
    actual = transport.read_chunk()
    expected_error = bytes.fromhex("42789a0005027b743563")
    assert actual == expected_error.ljust(len(actual), b"\x00")
