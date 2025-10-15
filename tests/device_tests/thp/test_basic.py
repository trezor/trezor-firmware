import pytest

from trezorlib import messages
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.mapping import DEFAULT_MAPPING
from trezorlib.transport import Transport, Timeout
from trezorlib import protocol_v1
from trezorlib.thp.message import Message
from trezorlib.thp import control_byte, thp_io

pytestmark = [
    pytest.mark.protocol("thp"),
    pytest.mark.setup_client(uninitialized=True),
]


def write_padded(transport: Transport, msg: bytes):
    assert transport.CHUNK_SIZE is not None
    padded = msg.ljust(transport.CHUNK_SIZE, b"\x00")
    transport.write_chunk(padded)


def test_v1(client: Client):
    # There should be a failure response to received init packet (starts with "?##")
    write_padded(client.transport, b"?## Init packet")
    res_id, res_data = protocol_v1.read(client.transport)
    res = DEFAULT_MAPPING.decode(res_id, res_data)
    assert res == messages.Failure(code=messages.FailureType.InvalidProtocol)

    # There should be no response for continuation packet (starts with "?" only)
    write_padded(client.transport, b"? Cont packet")
    with pytest.raises(Timeout):
        client.transport.read_chunk(timeout=0.1)


def test_v2_unallocated(client: Client):
    # A message to unallocated THP channel 0x789a should result in an error
    message = Message(
        cid=0x789A,
        ctrl_byte=control_byte.HANDSHAKE_INIT_REQ,
        data=bytes.fromhex("0011223344556677"),
    )
    write_padded(client.transport, message.to_bytes())
    response = thp_io.read(client.transport, timeout=0.1)
    assert response.cid == 0x789A
    assert response.ctrl_byte == control_byte.ERROR
    assert response.data == b"\x02"
