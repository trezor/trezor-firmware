import pytest

from . import common
from trezorlib.client import TrezorClient


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
