# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

from .common import *
import trezorlib.ckd_public as bip32


class TestMsgGetpublickey(TrezorTest):

    def test_btc(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert bip32.serialize(self.client.get_public_node([]).node, 0x0488B21E) == 'xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy'
        assert self.client.get_public_node([], coin_name='Bitcoin').xpub == 'xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy'
        assert bip32.serialize(self.client.get_public_node([1]).node, 0x0488B21E) == 'xpub68zNxjsTrV8y9AadThLW7dTAqEpZ7xBLFSyJ3X9pjTv6Njg6kxgjXJkzxq8u3ttnjBw1jupQHMP3gpGZzZqd1eh5S4GjkaMhPR18vMyUi8N'
        assert self.client.get_public_node([1], coin_name='Bitcoin').xpub == 'xpub68zNxjsTrV8y9AadThLW7dTAqEpZ7xBLFSyJ3X9pjTv6Njg6kxgjXJkzxq8u3ttnjBw1jupQHMP3gpGZzZqd1eh5S4GjkaMhPR18vMyUi8N'
        assert bip32.serialize(self.client.get_public_node([0, -1]).node, 0x0488B21E) == 'xpub6A3FoZqYXj1AbW4thRwBh26YwZWbmoyjTaZwwxJjY1oKUpefLepL3RFS9DHKQrjAfxDrzDepYMDZPqXN6upQm3bHQ9xaXD5a3mqni3goF4v'
        assert self.client.get_public_node([0, -1], coin_name='Bitcoin').xpub == 'xpub6A3FoZqYXj1AbW4thRwBh26YwZWbmoyjTaZwwxJjY1oKUpefLepL3RFS9DHKQrjAfxDrzDepYMDZPqXN6upQm3bHQ9xaXD5a3mqni3goF4v'
        assert bip32.serialize(self.client.get_public_node([-9, 0]).node, 0x0488B21E) == 'xpub6A2h5mzLDfYginoD7q7wCWbq18wTbN9gducRr2w5NRTwdLeoT3cJSwefFqW7uXTpVFGtpUyDMBNYs3DNvvXx6NPjF9YEbUQrtxFSWnPtVrv'
        assert self.client.get_public_node([-9, 0], coin_name='Bitcoin').xpub == 'xpub6A2h5mzLDfYginoD7q7wCWbq18wTbN9gducRr2w5NRTwdLeoT3cJSwefFqW7uXTpVFGtpUyDMBNYs3DNvvXx6NPjF9YEbUQrtxFSWnPtVrv'
        assert bip32.serialize(self.client.get_public_node([0, 9999999]).node, 0x0488B21E) == 'xpub6A3FoZqQEK6iwLZ4HFkqSo5fb35BH4bpjC4SPZ63prfLdGYPwYxEuC6o91bUvFFdMzKWe5rs3axHRUjxJaSvBnKKFtnfLwDACRxPxabsv2r'
        assert self.client.get_public_node([0, 9999999], coin_name='Bitcoin').xpub == 'xpub6A3FoZqQEK6iwLZ4HFkqSo5fb35BH4bpjC4SPZ63prfLdGYPwYxEuC6o91bUvFFdMzKWe5rs3axHRUjxJaSvBnKKFtnfLwDACRxPxabsv2r'

    def test_ltc(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert bip32.serialize(self.client.get_public_node([]).node, 0x019DA462) == 'Ltub2SSUS19CirucVPGDKDBatBDBEM2s9UbH66pBURfaKrMocCPLhQ7Z7hecy5VYLHA5fRdXwB2e61j2VJCNzVsqKTCVEU1vECjqi5EyczFX9xp'
        assert self.client.get_public_node([], coin_name='Litecoin').xpub == 'Ltub2SSUS19CirucVPGDKDBatBDBEM2s9UbH66pBURfaKrMocCPLhQ7Z7hecy5VYLHA5fRdXwB2e61j2VJCNzVsqKTCVEU1vECjqi5EyczFX9xp'
        assert bip32.serialize(self.client.get_public_node([1]).node, 0x019DA462) == 'Ltub2VRVRP5VjvSyPXra4BLVyVZPv397sjhUNjBGsbtw6xko77JuQyBULxFSKheviJJ3KQLbL3Cx8P2RnudguTw4raUVjCACRG7jsumUptYx55C'
        assert self.client.get_public_node([1], coin_name='Litecoin').xpub == 'Ltub2VRVRP5VjvSyPXra4BLVyVZPv397sjhUNjBGsbtw6xko77JuQyBULxFSKheviJJ3KQLbL3Cx8P2RnudguTw4raUVjCACRG7jsumUptYx55C'
        assert bip32.serialize(self.client.get_public_node([0, -1]).node, 0x019DA462) == 'Ltub2WUNGD3aRAKAqsLqHuwBYtCn2MqAXbVsarmvn33quWe2DCHTzfK4s4jsW5oM5G8RGAdSaM3NPNrwVvtV1ourbyNhhHr3BtqcYGc8caf5GoT'
        assert self.client.get_public_node([0, -1], coin_name='Litecoin').xpub == 'Ltub2WUNGD3aRAKAqsLqHuwBYtCn2MqAXbVsarmvn33quWe2DCHTzfK4s4jsW5oM5G8RGAdSaM3NPNrwVvtV1ourbyNhhHr3BtqcYGc8caf5GoT'
        assert bip32.serialize(self.client.get_public_node([-9, 0]).node, 0x019DA462) == 'Ltub2WToYRCN76rgyA59iK7w4Ni45wG2M9fpmBpQg7gBjvJeMiHc7473Gb96ci29Zvs55TgUQcMmCD1vy8aVqpdPwJB9YHRhGAAuPT1nRLLXmFu'
        assert self.client.get_public_node([-9, 0], coin_name='Litecoin').xpub == 'Ltub2WToYRCN76rgyA59iK7w4Ni45wG2M9fpmBpQg7gBjvJeMiHc7473Gb96ci29Zvs55TgUQcMmCD1vy8aVqpdPwJB9YHRhGAAuPT1nRLLXmFu'
        assert bip32.serialize(self.client.get_public_node([0, 9999999]).node, 0x019DA462) == 'Ltub2WUNGD3S7kQjBhpzsjkqJfBtfqPk2r7xrUGRDdqACMW3MeBCbZSyiqbEVt7WaeesxCj6EDFQtcbfXa75DUYN2i6jZ2g81cyCgvijs9J2u2n'
        assert self.client.get_public_node([0, 9999999], coin_name='Litecoin').xpub == 'Ltub2WUNGD3S7kQjBhpzsjkqJfBtfqPk2r7xrUGRDdqACMW3MeBCbZSyiqbEVt7WaeesxCj6EDFQtcbfXa75DUYN2i6jZ2g81cyCgvijs9J2u2n'

    def test_tbtc(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert bip32.serialize(self.client.get_public_node([111, 42]).node, 0x043587CF) == 'tpubDAgixSyai5PWbc8N1mBkHDR5nLgAnHFtY7r4y5EzxqAxrt9YUDpZL3kaRoHVvCfrcwNo31c2isBP2uTHcZxEosuKbyJhCAbrvGoPuLUZ7Mz'
        assert self.client.get_public_node([111, 42], coin_name='Testnet').xpub == 'tpubDAgixSyai5PWbc8N1mBkHDR5nLgAnHFtY7r4y5EzxqAxrt9YUDpZL3kaRoHVvCfrcwNo31c2isBP2uTHcZxEosuKbyJhCAbrvGoPuLUZ7Mz'
