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

import time

import pytest

from trezorlib import btc
from trezorlib.tools import H_


@pytest.mark.flaky(max_runs=5)
class TestBip32Speed:
    @pytest.mark.skip_t2
    def test_public_ckd(self, client):
        btc.get_address(client, "Bitcoin", [])  # to compute root node via BIP39

        for depth in range(8):
            start = time.time()
            btc.get_address(client, "Bitcoin", range(depth))
            delay = time.time() - start
            expected = (depth + 1) * 0.26
            print("DEPTH", depth, "EXPECTED DELAY", expected, "REAL DELAY", delay)
            assert delay <= expected

    @pytest.mark.skip_t2
    def test_private_ckd(self, client):
        btc.get_address(client, "Bitcoin", [])  # to compute root node via BIP39

        for depth in range(8):
            start = time.time()
            address_n = [H_(-i) for i in range(-depth, 0)]
            btc.get_address(client, "Bitcoin", address_n)
            delay = time.time() - start
            expected = (depth + 1) * 0.26
            print("DEPTH", depth, "EXPECTED DELAY", expected, "REAL DELAY", delay)
            assert delay <= expected

    @pytest.mark.skip_t2
    def test_cache(self, client):
        start = time.time()
        for x in range(10):
            btc.get_address(client, "Bitcoin", [x, 2, 3, 4, 5, 6, 7, 8])
        nocache_time = time.time() - start

        start = time.time()
        for x in range(10):
            btc.get_address(client, "Bitcoin", [1, 2, 3, 4, 5, 6, 7, x])
        cache_time = time.time() - start

        print("NOCACHE TIME", nocache_time)
        print("CACHED TIME", cache_time)

        # Cached time expected to be at least 2x faster
        assert cache_time <= nocache_time / 2.0
