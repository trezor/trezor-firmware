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

from trezorlib import messages as proto, nem2
from trezorlib.tools import parse_path

from ..common import MNEMONIC12

@pytest.mark.altcoin
@pytest.mark.nem2
class TestMsgNEM2SignTxTransfer:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_transfer(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_TRANSACTION_TRANSFER,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "recipientAddress": {
                    "address": "TAO6QEUC3APBTMDAETMG6IZJI7YOXWHLGC5T4HA4",
                    "networkType": nem2.NETWORK_TYPE_TEST_NET
                },
                "mosaics": [
                    {
                        "amount": "1000000000",
                        "id": "308F144790CD7BC4"
                    }
                ],
                "message": {
                    "type": 0,
                    "payload": "Test Transfer"
                }
            }
        )

        assert (
            tx.payload.hex().upper()
            == "BE000000000000000C397469A66B2E6B0F43146D955FE076E89DC63A452642ADC11DA690DA634616DC9004ED46887B1A9B6F23781B906F8AADCB01D2873CB4F329E922ECC002EF05A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001985441204E000000000000090A1E5E1A000000981DE81282D81E19B06024D86F232947F0EBD8EB30BB3E1C1C010E0000000000C47BCD9047148F3000CA9A3B000000000054657374205472616E73666572"
        )
        assert (
            tx.hash.hex().upper()
            == "E11553B8FDA4D47762E803B1A63AD68E35A1D2B240E4C0B9A6B0C11625BA58D3"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_transfer_encrypted_message(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_TRANSACTION_TRANSFER,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "recipientAddress": {
                    "address": "TB6YHDGPYV3TGEFE7Z3BH2EXJZNVJJTH3EWL76PD",
                    "networkType": nem2.NETWORK_TYPE_TEST_NET
                },
                "mosaics": [
                    {
                        "amount": "1000000000",
                        "id": "85BBEA6CC462B244"
                    }
                ],
                "message": {
                    "type": 1,
                    "payload": "9FB270F6EF609FD70B469F4139B0456ACE22A081B68B01106F4D08C756B7F7A7D84C470AADA2361D7BF3732D47E7973490FC4EC97511C5EA20A2F590795736A2"
                }
            }
        )

        assert (
            tx.payload.hex().upper()
            == "310100000000000085F613924C0A0E010B3A463C7E1445730EDD30636852653E03FB2EB9C13F13BAA7FD5B3E1449EC6E854CC2AA7F0453FD287037B05D2CFCB7B6BA3DCA0915C609A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001985441204E000000000000090A1E5E1A000000987D838CCFC5773310A4FE7613E8974E5B54A667D92CBFF9E30181000000000044B262C46CEABB8500CA9A3B00000000013946423237304636454636303946443730423436394634313339423034353641434532324130383142363842303131303646344430384337353642374637413744383443343730414144413233363144374246333733324434374537393733343930464334454339373531314335454132304132463539303739353733364132"
        )
        assert (
            tx.hash.hex().upper()
            == "7ACDA4241C878445A5263569B4B9A61382719518FDF93856F8B57824F55162C5"
        )
