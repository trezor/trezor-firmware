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
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path


@pytest.mark.skip_t1
def test_get_viewing_key(client: Client):
    # Testnet
    z_address_n = parse_path("m/32h/1h/50h")
    fvk = zcash.get_viewing_key(client, z_address_n, "Zcash Testnet", full=True)
    assert (
        fvk
        == "uviewtest1pw6statq3g7pnfusxz4f0txyuma4xnzj8u9dy9deq5qk0vvdg584c0n3wxpqy9v3ky2su5uzhz6nqn9nhsgjgv9kjquvezvfxcsg38m93k38qwrr3563whrqfgsfd3hfvzlfgxdxkt46xxyqar0zrq7fflnekjzwlpu98fgv0mpvnh6cn86gvmqprx6al"
    )
    ivk = zcash.get_viewing_key(client, z_address_n, "Zcash Testnet", full=False)
    assert (
        ivk
        == "uivktest1vcysjf7k94zt9qt0psny3sdtkl5psrrpw3hf40qlzhc3r7uqdwgy30rcqrcqe4sayp4h88efnuutd87nwau2vgq2agytktlz90n7vmpfahpg4arg0zdusyjkknq0lu2xeumsl8rrqr"
    )

    z_address_n = parse_path("m/32h/1h/2h")
    fvk = zcash.get_viewing_key(client, z_address_n, "Zcash Testnet", full=True)
    assert (
        fvk
        == "uviewtest1zn0yvwlvtt4nkd584lgs0h4q023e5q5jfm0an24l6z4kkpsupkuwuwa3c56ktrzlpwddeetaqzua64pux6m6jt8kc6rf2p0dvju2rrgye7xag2293d27umt8trmg8fdx6hug04lstk4knezc556gzpygg29sp999u7a33f0sapxmv404h39736sp202mm"
    )
    ivk = zcash.get_viewing_key(client, z_address_n, "Zcash Testnet", full=False)
    assert (
        ivk
        == "uivktest13n83gqvgfupx4vqlyp2frg4p6cwl90du5c4j0xhl3vut627jeltmqrs3ufvls82vep36cyupf290xp33u9cfxfj9nhrnxa0032avw9cses7texrqp080vpn3hf3htkvd7ttqjl63ky"
    )

    z_address_n = parse_path("m/32h/1h/43h")
    fvk = zcash.get_viewing_key(client, z_address_n, "Zcash Testnet", full=True)
    assert (
        fvk
        == "uviewtest129xz6htykx2ls97j0shuj8wpxuqr40apqskvatjtucc92nj5xu56wtrn957gy087mcg3uawzc4s6n2vkq8qtqnnrxqx3ttjje0hm08whlr2htr4l6ykq8e773750ashrk8kc4fh4hqtdlgch07u2yrsukmgkstd7cldtgpscrdf335c38xls67gkyj6ng"
    )
    ivk = zcash.get_viewing_key(client, z_address_n, "Zcash Testnet", full=False)
    assert (
        ivk
        == "uivktest1x7nr2cg8alscrh6tdnh99knfz5tz0ugy245fwkf6ywzw7pqaf5agphhxe9pjuvz7dtgh9hyhky0uwwrs97x6vp5n3cd2r3l2vk8ya0c9rmf49pugrup4nv7qfllf5t8927mq9thphh"
    )

    # Mainnet
    z_address_n = parse_path("m/32h/133h/98h")
    fvk = zcash.get_viewing_key(client, z_address_n, "Zcash", full=True)
    assert (
        fvk
        == "uview1ktrwqfr0hk7tstlun43k5zsp96j0hs2l38vlxhr67ug22ak863ecxxdx9hysamhf039sqrgq4vl9527nuu3g3pw72aleazl4g0afzrqlq0gwg7284tlt6gm5hf69g7yv07hmcp3kkqm50dltlgcxdl460zvle5c6xpsh98fxpu2cguq66zlkvfc8ae256"
    )
    ivk = zcash.get_viewing_key(client, z_address_n, "Zcash", full=False)
    assert (
        ivk
        == "uivk14e0a0xa80tv6l6z0a7jcqkpm8cuuta59p9n5kf79t9mcx50mcz9mrwspyv4ffev3auxqp52hmyje8alnrv6fxk2nav5ujjuraxenejrhdv6a2kfrkmpsf2gf4lsx6xakqvpse68plp"
    )

    z_address_n = parse_path("m/32h/133h/0h")
    fvk = zcash.get_viewing_key(client, z_address_n, "Zcash", full=True)
    assert (
        fvk
        == "uview1sm5jrljgqsuzfxaqk53dt2u273fawaxzratjpfhmt2he954p7p6z07n9uz65z47af9zcupldhqx2qdn0p90p2wceatwhff6dthfxwnyua6v84tjgf7dftvzz5fs87hcuru0k4qfuhra4dvxf2rmhm7wp8d27pqfyf7n3larlc8pxhu6l4uv4rysaz492u"
    )
    ivk = zcash.get_viewing_key(client, z_address_n, "Zcash", full=False)
    assert (
        ivk
        == "uivk13lms6pd4ddsrvkr8p830nfvvm0tggnt62pjj2wzvj3q4cs0a76keky8cdcfkpsf0mdr9p4e9rusaasjw5qv3pr93ey86rgmlsvg39jss3klpg9v46s4e38gacq2nhltge4xq7ep5kv"
    )

    z_address_n = parse_path("m/32h/133h/86h")
    fvk = zcash.get_viewing_key(client, z_address_n, "Zcash", full=True)
    assert (
        fvk
        == "uview1wfy9lsk7nvpxjmuadvemskrg340ld37fqw3nxht9s570g49y3w4kc2e3pew6gzd84nejzyg3h80vqpytc3gjlfzn9v7gdluurnv82uldgnydnx9xup03rq465038x7n3jwtl0c2ad4e4kc8075na5efwmtkay2mvu7kzsy2npvrtg97y76gjtlcc924km"
    )
    ivk = zcash.get_viewing_key(client, z_address_n, "Zcash", full=False)
    assert (
        ivk
        == "uivk1u5q0jldl3g45gfmxgrk8wkewxzkdyp60ng0rk6xh73nu3j9uhxn6yh4w07kka8a2wgjyes773czpvkvf7ujjntxhqnjd3keygcqpc4jnxt030gf64jlcr2rx4esalp5s0xmq2njg0r"
    )
