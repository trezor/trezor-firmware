import functools
import os
import pytest

from trezorlib.transport import get_transport
from trezorlib.client import TrezorClient, TrezorClientDebugLink
from trezorlib import log, coins


def get_device():
    path = os.environ.get('TREZOR_PATH')
    return get_transport(path)


def device_version():
    device = get_device()
    if not device:
        raise RuntimeError()
    client = TrezorClient(device)
    if client.features.model == "T":
        return 2
    else:
        return 1


TREZOR_VERSION = device_version()


@pytest.fixture(scope="function")
def client():
    wirelink = get_device()
    debuglink = wirelink.find_debug()
    client = TrezorClientDebugLink(wirelink)
    client.set_debuglink(debuglink)
    client.set_tx_api(coins.tx_api['Bitcoin'])
    client.wipe_device()
    client.transport.session_begin()

    yield client

    client.transport.session_end()


def setup_client(mnemonic=None, pin='', passphrase=False):
    if mnemonic is None:
        mnemonic = ' '.join(['all'] * 12)
    if pin is True:
        pin = '1234'

    def client_decorator(function):
        @functools.wraps(function)
        def wrapper(client, *args, **kwargs):
            client.load_device_by_mnemonic(mnemonic=mnemonic, pin=pin, passphrase_protection=passphrase, label='test', language='english')
            return function(client, *args, **kwargs)
        return wrapper

    return client_decorator


def pytest_configure(config):
    if config.getoption('verbose'):
        log.enable_debug_output()


def pytest_addoption(parser):
    parser.addini("run_xfail", "List of markers that will run even if marked as xfail", "args", [])


def pytest_runtest_setup(item):
    """
    Called for each test item (class, individual tests).

    Performs custom processing, mainly useful for trezor CI testing:
    * 'skip_t2' tests are skipped on T2 and 'skip_t1' tests are skipped on T1.
    * no test should have both skips at the same time
    * allows to 'runxfail' tests specified by 'run_xfail' in pytest.ini
    """
    if item.get_marker("skip_t1") and item.get_marker("skip_t2"):
        pytest.fail("Don't skip tests for both trezors!")

    if item.get_marker("skip_t2") and TREZOR_VERSION == 2:
        pytest.skip("Test excluded on Trezor T")
    if item.get_marker("skip_t1") and TREZOR_VERSION == 1:
        pytest.skip("Test excluded on Trezor 1")

    xfail = item.get_marker("xfail")
    run_xfail = any(item.get_marker(marker) for marker in item.config.getini("run_xfail"))
    if xfail and run_xfail:
        # Deep hack: pytest's private _evalxfail helper determines whether the test should xfail or not.
        # The helper caches its result even before this hook runs.
        # Here we force-set the result to False, meaning "test does NOT xfail, run as normal"
        # IOW, this is basically per-item "--runxfail"
        item._evalxfail.result = False
