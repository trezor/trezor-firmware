from trezorlib import btc, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...common import is_core
from ...input_flows import InputFlowConfirmAllWarnings


def test_singlesig_p2wsh(client: Client):
    with client:
        if is_core(client):
            IF = InputFlowConfirmAllWarnings(client)
            client.set_input_flow(IF.get())

        btc.get_address(
            client,
            "Bitcoin",
            parse_path("m/45h/0/0/0/0/0"),
            script_type=messages.InputScriptType.SPENDP2SHWITNESS,
            show_display=True,
        )
