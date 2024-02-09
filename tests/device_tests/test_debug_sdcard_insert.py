import pytest

from trezorlib.debuglink import TrezorClientDebugLink as Client

pytestmark = [pytest.mark.skip_t1, pytest.mark.skip_tr]


@pytest.mark.sd_card(formatted=True)
def test_sd_eject(client: Client):
    assert client.features.sd_card_present is True

    client.debug.eject_sd_card()
    client.refresh_features()
    assert client.features.sd_card_present is False

    client.debug.insert_sd_card(2)
    client.debug.erase_sd_card(format=True)
    client.refresh_features()
    assert client.features.sd_card_present is True

    client.debug.eject_sd_card()
    client.refresh_features()
    assert client.features.sd_card_present is False

    client.debug.insert_sd_card(3)
    client.debug.erase_sd_card(format=False)
    client.refresh_features()
    assert client.features.sd_card_present is True

    client.debug.eject_sd_card()
    client.refresh_features()
    assert client.features.sd_card_present is False
