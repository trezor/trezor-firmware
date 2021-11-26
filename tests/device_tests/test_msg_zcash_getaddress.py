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

import pytest

from trezorlib import zcash
from trezorlib.tools import parse_path

from ..common import MNEMONIC12


@pytest.mark.altcoin
@pytest.mark.zcash
@pytest.mark.skip_t1
class TestMsgZcashGetaddress:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_zcash_getaddress(self, client):
        assert (
            zcash.get_address(client, t_address_n=parse_path("m/44h/1h/0h/0/0"), show_display=True)
            == "tmF2pJ7nLJA8N7WjQiRyjTBWmUR1VztVHt1"
        )
        assert (
            zcash.get_address(client, t_address_n=parse_path("m/44h/133h/0h/0/0"), show_display=True)
            == "t1NKu7kH5nQNPu1JVh7FuPhAHyqKZRpnpBq"
        )
        # TODO: add real unified addresses test vectors
        assert (
            zcash.get_address(client, z_address_n=parse_path("m/32h/1h/0h"), show_display=True)
            == "utest127kqmkhd8ra505pgey5p0cj3u75gjwr0h3qnapw2w4vahje6t972cdu3zthy35dl3k22jn9qdup8tlhhe7gsde07zttp6kl3859p7drx"
        )
        assert (
            zcash.get_address(client, t_address_n=parse_path("m/44h/1h/0h/0/0"), z_address_n=parse_path("m/32h/1h/0h"), show_display=True)
            == "utest1aqy7da29u6jffqu3tfttgh5hvhmswrftw09sregcv8hr2mdrdrqmlylukprfcp6a2al5eu3yl4hn3c4a5mkwvfqkqj8j3g2nlz54ztzrmltd4dz26yzwvvxfs2k8uc998kgr5rrze7e"
        )   
        assert (
            zcash.get_address(client, z_address_n=parse_path("m/32h/133h/0h"), show_display=True)
            == "u128xx4m082yc34nv2a68gc42kttpdqzj7tfswywl4vseleujnc5d2zjygw9zwtrqmcg2uhv0ku5syech3qng5qvxgdxkgm5prxclzj7qc"
        )
        assert (
            zcash.get_address(client, t_address_n=parse_path("m/44h/133h/0h/0/0"), z_address_n=parse_path("m/32h/133h/0h"), show_display=True)
            == "u173h2sx3vd54hh4pfnhskwu3xf6x57cz2yhghvvrjctu54ef2tjng3v02f9xrnyhhhzga3v4qrwhr22qu2pk0tqx8ja2whg2lttandeer035k3ycaym7la0n5k9dfhgzld5hskw9356q"
        )
        # TODO: deversifier index tests        