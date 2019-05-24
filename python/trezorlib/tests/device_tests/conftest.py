# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import functools
import os

import pytest

from trezorlib import debuglink, log
from trezorlib.debuglink import TrezorClientDebugLink
from trezorlib.device import wipe as wipe_device
from trezorlib.transport import enumerate_devices, get_transport

TREZOR_VERSION = None


def get_device():
    path = os.environ.get("TREZOR_PATH")
    if path:
        transport = get_transport(path)
    else:
        devices = enumerate_devices()
        for device in devices:
            if hasattr(device, "find_debug"):
                transport = device
                break
        else:
            raise RuntimeError("No debuggable device found")
    env_interactive = int(os.environ.get("INTERACT", 0))
    try:
        return TrezorClientDebugLink(transport, auto_interact=not env_interactive)
    except Exception as e:
        raise RuntimeError(
            "Failed to open debuglink for {}".format(transport.get_path())
        ) from e


def device_version():
    client = get_device()
    if client.features.model == "T":
        return 2
    else:
        return 1


@pytest.fixture(scope="function")
def client():
    client = get_device()
    wipe_device(client)

    client.open()
    yield client
    client.close()


def setup_client(mnemonic=None, pin="", passphrase=False):
    if mnemonic is None:
        mnemonic = " ".join(["all"] * 12)
    if pin is True:
        pin = "1234"

    def client_decorator(function):
        @functools.wraps(function)
        def wrapper(client, *args, **kwargs):
            debuglink.load_device_by_mnemonic(
                client,
                mnemonic=mnemonic,
                pin=pin,
                passphrase_protection=passphrase,
                label="test",
                language="english",
            )
            return function(client, *args, **kwargs)

        return wrapper

    return client_decorator


def pytest_configure(config):
    global TREZOR_VERSION
    TREZOR_VERSION = device_version()

    if config.getoption("verbose"):
        log.enable_debug_output()


def pytest_addoption(parser):
    parser.addoption(
        "--interactive",
        action="store_true",
        help="Wait for user to do interaction manually",
    )


def pytest_runtest_setup(item):
    """
    Called for each test item (class, individual tests).

    Performs custom processing, mainly useful for trezor CI testing:
    * 'skip_t2' tests are skipped on T2 and 'skip_t1' tests are skipped on T1.
    * no test should have both skips at the same time
    """
    if item.get_closest_marker("skip_t1") and item.get_closest_marker("skip_t2"):
        pytest.fail("Don't skip tests for both trezors!")

    if item.get_closest_marker("skip_t2") and TREZOR_VERSION == 2:
        pytest.skip("Test excluded on Trezor T")
    if item.get_closest_marker("skip_t1") and TREZOR_VERSION == 1:
        pytest.skip("Test excluded on Trezor 1")
