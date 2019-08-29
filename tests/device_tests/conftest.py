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

import filecmp
import itertools
import os
import re
from pathlib import Path

import pytest

from trezorlib import debuglink, log
from trezorlib.debuglink import TrezorClientDebugLink
from trezorlib.device import apply_settings, wipe as wipe_device
from trezorlib.messages.PassphraseSourceType import HOST as PASSPHRASE_ON_HOST
from trezorlib.transport import enumerate_devices, get_transport

TREZOR_VERSION = None

SAVE_SCREEN = int(os.environ.get("TREZOR_SAVE_SCREEN", 0))
SAVE_SCREEN_FIXTURES = int(os.environ.get("TREZOR_SAVE_SCREEN_FIXTURES", 0))


class ScreenshotCollector:
    SCREENSHOT_PATH = (Path(__file__) / "../../../core/src").resolve()
    SCREENSHOT_FIXTURE_PATH = (Path(__file__) / "../../ui_tests").resolve()

    def __init__(self, node):
        self.node = node

    @staticmethod
    def _remove_files(files):
        for f in files:
            print("Removing", f)
            f.unlink()

    def get_test_dirname(self):
        # This composes the dirname from the test module name and test item name.
        # Test item name is usually function name, but when parametrization is used,
        # parameters are also part of the name. Some functions have very long parameter
        # names (tx hashes etc) that run out of maximum allowable filename length, so
        # we limit the name to first 100 chars. This is not a problem with txhashes.
        node_name = re.sub(r"\W+", "_", self.node.name)[:100]
        node_module_name = self.node.getparent(pytest.Module).name
        return "{}_{}".format(node_module_name, node_name)

    def collect_screenshots(self):
        return list(sorted(self.SCREENSHOT_PATH.glob("*.png")))

    def collect_fixtures(self):
        return list(
            sorted(
                self.SCREENSHOT_FIXTURE_PATH.glob(
                    "{}/*.png".format(self.get_test_dirname())
                )
            )
        )

    def assert_images(self):
        fixtures = self.collect_fixtures()
        if not fixtures:
            return
        images = self.collect_screenshots()

        for fixture, image in itertools.zip_longest(fixtures, images):
            if fixture is None:
                pytest.fail("Missing fixture for image {}".format(image))
            if image is None:
                pytest.fail("Missing image for fixture {}".format(fixture))
            if not filecmp.cmp(fixture, image):
                pytest.fail("Image {} and fixture {} differ".format(image, fixture))

    def record_fixtures(self):
        fixture_dir = self.SCREENSHOT_FIXTURE_PATH / self.get_test_dirname()

        if fixture_dir.is_dir():
            # remove old fixtures
            self._remove_files(self.collect_fixtures())
        else:
            # create the fixture dir, if not present
            print("Creating", fixture_dir)
            fixture_dir.mkdir()

        # move the recorded images into the fixture locations
        for index, image in enumerate(self.collect_screenshots()):
            fixture = fixture_dir / "{}.png".format(index)
            print("Saving", image, "into", fixture)
            image.replace(fixture)

    def __enter__(self):
        if SAVE_SCREEN:
            self._remove_files(self.collect_screenshots())

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is None and SAVE_SCREEN:
            if SAVE_SCREEN_FIXTURES:
                self.record_fixtures()
            else:
                self.assert_images()

        # self._remove_files(self.collect_screenshots())


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

    with ScreenshotCollector(request.node):
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
