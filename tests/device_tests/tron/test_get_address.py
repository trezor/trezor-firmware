import pytest

from trezorlib import tron
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import InputFlowShowAddressQRCode

pytestmark = [pytest.mark.altcoin, pytest.mark.tron, pytest.mark.models("core")]


@parametrize_using_common_fixtures("tron/get_address.json")
def test_get_address(client: Client, parameters, result):
    address_n = parse_path(parameters["path"])
    address = tron.get_address(client, address_n, show_display=True)
    assert address == result["address"]


@parametrize_using_common_fixtures("tron/get_address.json")
def test_get_address_chunkify_details(client: Client, parameters, result):
    with client:
        IF = InputFlowShowAddressQRCode(client)
        client.set_input_flow(IF.get())
        address_n = parse_path(parameters["path"])
        address = tron.get_address(client, address_n, show_display=True, chunkify=True)
        assert address == result["address"]
