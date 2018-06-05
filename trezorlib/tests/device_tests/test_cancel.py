import pytest

from .conftest import setup_client
import trezorlib.messages as m


@setup_client()
@pytest.mark.parametrize("message", [
    m.Ping(message="hello", button_protection=True),
    m.GetAddress(
        address_n=[0],
        coin_name="Bitcoin",
        script_type=m.InputScriptType.SPENDADDRESS,
        show_display=True
    ),
])
def test_cancel_message(client, message):
    resp = client.call_raw(message)
    assert isinstance(resp, m.ButtonRequest)

    client.transport.write(m.ButtonAck())
    client.transport.write(m.Cancel())

    resp = client.transport.read()

    assert isinstance(resp, m.Failure)
    assert resp.code == m.FailureType.ActionCancelled
