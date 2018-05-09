import pytest

from . import common
from trezorlib.client import TrezorClient
from trezorlib import log


def device_version():
    device = common.get_device()
    if not device:
        raise RuntimeError()
    client = TrezorClient(device)
    if client.features.model == "T":
        return 2
    else:
        return 1


try:
    TREZOR_VERSION = device_version()
except:
    raise
    TREZOR_VERSION = None


def pytest_configure(config):
    if config.getoption('verbose'):
        log.enable_debug_output()


def pytest_runtest_setup(item):
    '''
    Called for each test item (class, individual tests).
    Ensures that 'skip_t2' tests are skipped on T2
    and 'skip_t1' tests are skipped on T1.
    '''
    if item.get_marker("skip_t2") and TREZOR_VERSION == 2:
        pytest.skip("Test excluded on Trezor T")
    if item.get_marker("skip_t1") and TREZOR_VERSION == 1:
        pytest.skip("Test excluded on Trezor 1")
