# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import os

import pytest

from trezorlib import debuglink, log
from trezorlib.debuglink import TrezorClientDebugLink
from trezorlib.device import apply_settings, wipe as wipe_device
from trezorlib.messages.PassphraseSourceType import HOST as PASSPHRASE_ON_HOST
from trezorlib.transport import enumerate_devices, get_transport

TREZOR_VERSION = None


def get_device():
    path = os.environ.get("TREZOR_PATH")
    interact = int(os.environ.get("INTERACT", 0))
    if path:
        try:
            transport = get_transport(path)
            return TrezorClientDebugLink(transport, auto_interact=not interact)
        except Exception as e:
            raise RuntimeError("Failed to open debuglink for {}".format(path)) from e

    else:
        devices = enumerate_devices()
        for device in devices:
            try:
                return TrezorClientDebugLink(device, auto_interact=not interact)
            except Exception:
                pass
        else:
            raise RuntimeError("No debuggable device found")


def device_version():
    client = get_device()
    if client.features.model == "T":
        return 2
    else:
        return 1


@pytest.fixture(scope="function")
def client(request):
    client = get_device()
    wipe_device(client)

    client.open()

    # fmt: off
    setup_params = dict(
        uninitialized=False,
        mnemonic=" ".join(["all"] * 12),
        pin=None,
        passphrase=False,
    )
    # fmt: on

    marker = request.node.get_closest_marker("setup_client")
    if marker:
        setup_params.update(marker.kwargs)

    if not setup_params["uninitialized"]:
        if setup_params["pin"] is True:
            setup_params["pin"] = "1234"

        debuglink.load_device_by_mnemonic(
            client,
            mnemonic=setup_params["mnemonic"],
            pin=setup_params["pin"],
            passphrase_protection=setup_params["passphrase"],
            label="test",
            language="english",
        )
        client.clear_session()
        if setup_params["passphrase"] and client.features.model != "1":
            apply_settings(client, passphrase_source=PASSPHRASE_ON_HOST)

    yield client
    client.close()


def pytest_configure(config):
    # try to figure out trezor version
    global TREZOR_VERSION
    try:
        TREZOR_VERSION = device_version()
    except Exception:
        pass

    # register known markers
    config.addinivalue_line("markers", "skip_t1: skip the test on Trezor One")
    config.addinivalue_line("markers", "skip_t2: skip the test on Trezor T")
    config.addinivalue_line(
        "markers",
        'setup_client(mnemonic="all all all...", pin=None, passphrase=False, uninitialized=False): configure the client instance',
    )
    with open(os.path.join(os.path.dirname(__file__), "REGISTERED_MARKERS")) as f:
        for line in f:
            config.addinivalue_line("markers", line.strip())

    # enable debug
    if config.getoption("verbose"):
        log.enable_debug_output()


def pytest_runtest_setup(item):
    """
    Called for each test item (class, individual tests).

    Performs custom processing, mainly useful for trezor CI testing:
    * 'skip_t2' tests are skipped on T2 and 'skip_t1' tests are skipped on T1.
    * no test should have both skips at the same time
    """
    if TREZOR_VERSION is None:
        pytest.fail("No debuggable Trezor is available")

    if item.get_closest_marker("skip_t1") and item.get_closest_marker("skip_t2"):
        pytest.fail("Don't skip tests for both trezors!")

    skip_altcoins = int(os.environ.get("TREZOR_PYTEST_SKIP_ALTCOINS", 0))
    if item.get_closest_marker("altcoin") and skip_altcoins:
        pytest.skip("Skipping altcoin test")
    if item.get_closest_marker("skip_t2") and TREZOR_VERSION == 2:
        pytest.skip("Test excluded on Trezor T")
    if item.get_closest_marker("skip_t1") and TREZOR_VERSION == 1:
        pytest.skip("Test excluded on Trezor 1")
