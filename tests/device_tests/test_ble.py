import pytest

from trezorlib import ble
from trezorlib.debuglink import DebugSession as Session


@pytest.mark.models("t3w1")
def test_ble_unpair_all(session: Session):
    ble.unpair(session, all=True)
    # `Success` is sent before unpairing is done, so we'll send another command just to "flush" the last screen.
    session.client.ping("")
