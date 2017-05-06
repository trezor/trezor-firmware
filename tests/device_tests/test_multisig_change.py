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

import unittest
import common
import binascii
import itertools

import trezorlib.messages_pb2 as proto
import trezorlib.ckd_public as bip32
import trezorlib.types_pb2 as proto_types
from trezorlib.client import CallException

class TestMultisigChange(common.TrezorTest):

    node_ext1 = bip32.deserialize('xpub6E2LkiC2h7icfcjXPFDmwufDRaaTjTRYcS2nD7eGQeFx1WwZxxvCya5GefiJND6ddJnAjzzMusLcCnu6WyhZPrF6e5G71MWjNJVfs6u9csg')
    # m/1 => 02c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e
    # m/2 => 0375b9dfaad928ce1a7eed88df7c084e67d99e9ab74332419458a9a45779706801

    node_ext2 = bip32.deserialize('xpub6FKKCwdfD85eHmKn7d3mmbhqsHnGkB2n7Hmre29gbnR1cR4U1wrtf2akh1VVqjcTdfkxmwPjQyYPhLLgwBijfFPAYqTZzcjj4awB1BMUxq2')
    # m/1 => 0388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1
    # m/2 => 03a04f945d5a3685729dde697d574076de4bdf38e904f813b22a851548e1110fc0

    node_ext3 = bip32.deserialize('xpub69rsKg2fef3GzETrukhsR3U9i4nL3dXKy3cjSpm44Cg8waqrnyupanaLQt4bYjn2HTmH1NusFt9DAh6absMQqE4E66q7EYTyEsorZKXdWWx')
    # m/1 => 02e0c21e2a7cf00b94c5421725acff97f9826598b91f2340c5ddda730caca7d648
    # m/2 => 03928301ffb8c0d7a364b794914c716ba3107cc78a6fe581028b0d8638b22e8573

    node_int = bip32.deserialize('xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy')
    # m/1 => 0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6
    # m/2 => 038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3

    # ext1 + ext2 + int
        # redeemscript (2 of 3): 522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653ae
        # multisig address: 3Gj7y1FdTppx2JEDqYqAEZFnKCA4GRysKF
        # tx: d1d08ea63255af4ad16b098e9885a252632086fa6be53301521d05253ce8a73d
        # input 0: 0.001 BTC

    # ext1 + int + ext2
        # redeemscript (2 of 3): 522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c153ae
        # multisig address: 3QsvfB6d1LzYcpm8xyhS1N1HBRrzHTgLHB
        # tx: a6e2829d089cee47e481b1a753a53081b40738cc87e38f1d9b23ab57d9ad4396
        # input 0: 0.001 BTC

    # ext1 + ext3 + int
        # redeemscript (2 of 3): 522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e2102e0c21e2a7cf00b94c5421725acff97f9826598b91f2340c5ddda730caca7d648210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653ae
        # multisig address: 37LvC1Q5CyKbMbKMncEJdXxqGhHxrBEgPE
        # tx: e4bc1ae5e5007a08f2b3926fe11c66612e8f73c6b00c69c7027213b84d259be3
        # input 1: 0.001 BTC

    multisig_in1 = proto_types.MultisigRedeemScriptType(
                        pubkeys=[proto_types.HDNodePathType(node=node_ext1, address_n=[1]),
                                 proto_types.HDNodePathType(node=node_ext2, address_n=[1]),
                                 proto_types.HDNodePathType(node=node_int, address_n=[1])],
                        signatures=[b'', b'', b''],
                        m=2,
                        )

    multisig_in2 = proto_types.MultisigRedeemScriptType(
                        pubkeys=[proto_types.HDNodePathType(node=node_ext1, address_n=[1]),
                                 proto_types.HDNodePathType(node=node_int, address_n=[1]),
                                 proto_types.HDNodePathType(node=node_ext2, address_n=[1])],
                        signatures=[b'', b'', b''],
                        m=2,
                        )

    multisig_in3 = proto_types.MultisigRedeemScriptType(
                        pubkeys=[proto_types.HDNodePathType(node=node_ext1, address_n=[1]),
                                 proto_types.HDNodePathType(node=node_ext3, address_n=[1]),
                                 proto_types.HDNodePathType(node=node_int, address_n=[1])],
                        signatures=[b'', b'', b''],
                        m=2,
                        )

    inp1 = proto_types.TxInputType(address_n=[1],
                         prev_hash=binascii.unhexlify('d1d08ea63255af4ad16b098e9885a252632086fa6be53301521d05253ce8a73d'),
                         prev_index=0,
                         script_type=proto_types.SPENDMULTISIG,
                         multisig=multisig_in1,
                         )

    inp2 = proto_types.TxInputType(address_n=[1],
                         prev_hash=binascii.unhexlify('a6e2829d089cee47e481b1a753a53081b40738cc87e38f1d9b23ab57d9ad4396'),
                         prev_index=0,
                         script_type=proto_types.SPENDMULTISIG,
                         multisig=multisig_in2,
                         )

    inp3 = proto_types.TxInputType(address_n=[1],
                         prev_hash=binascii.unhexlify('e4bc1ae5e5007a08f2b3926fe11c66612e8f73c6b00c69c7027213b84d259be3'),
                         prev_index=1,
                         script_type=proto_types.SPENDMULTISIG,
                         multisig=multisig_in3,
                         )

    def _responses(self, inp1, inp2, change=0):
        resp = [
            proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
            proto.TxRequest(request_type=proto_types.TXMETA, details=proto_types.TxRequestDetailsType(tx_hash=inp1.prev_hash)),
            proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1, tx_hash=inp1.prev_hash)),
            proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
            proto.TxRequest(request_type=proto_types.TXMETA, details=proto_types.TxRequestDetailsType(tx_hash=inp2.prev_hash)),
            proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=inp2.prev_hash)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=inp2.prev_hash)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1, tx_hash=inp2.prev_hash)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
        ]
        if change != 1:
            resp.append(
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput)
            )
        resp.append(
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1))
        )
        if change != 2:
            resp.append(
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput)
            )
        resp += [
            proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
            proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
            proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
            proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
            proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
            proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
            proto.TxRequest(request_type=proto_types.TXFINISHED),
        ]
        return resp

    # both outputs are external
    def test_external_external(self):
        self.setup_mnemonic_nopin_nopassphrase()

        out1 = proto_types.TxOutputType(address='12iyMbUb4R2K3gre4dHSrbu5azG5KaqVss',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        out2 = proto_types.TxOutputType(address='17kTB7qSk3MupQxWdiv5ZU3zcrZc2Azes1',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        with self.client:
            self.client.set_expected_responses(self._responses(self.inp1, self.inp2))
            (_, serialized_tx) = self.client.sign_tx('Bitcoin', [self.inp1, self.inp2, ], [out1, out2, ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000023da7e83c25051d520133e56bfa86206352a285988e096bd14aaf5532a68ed0d100000000b500483045022100c4116c9a584083021dacb690d4d4938027cc3f2085dc15157162b589f2a0b52f02200bdec59f76376255afc7b76f759106f6f00edf0134db2a0ae5d28000ea517fd2014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653aeffffffff9643add957ab239b1d8fe387cc3807b48130a553a7b181e447ee9c089d82e2a600000000b400473044022044e77c67a5a78c8eb4f304cf23972a7763cce6f7dc3587d6e77e2aa05212ea6402200be874d39c32ad2475d03342cb0b164ec618297231c519186e3d0efde7a3374d014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c153aeffffffff02a0860100000000001976a91412e8391ad256dcdc023365978418d658dfecba1c88aca0860100000000001976a9144a087d89f8ad16ca029c675b037c02fd1c5f9aec88ac00000000')

    # first external, second internal
    def test_external_internal(self):
        self.setup_mnemonic_nopin_nopassphrase()

        out1 = proto_types.TxOutputType(address='12iyMbUb4R2K3gre4dHSrbu5azG5KaqVss',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        out2 = proto_types.TxOutputType(address_n=[4],
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        with self.client:
            self.client.set_expected_responses(self._responses(self.inp1, self.inp2, change=2))
            (_, serialized_tx) = self.client.sign_tx('Bitcoin', [self.inp1, self.inp2, ], [out1, out2, ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000023da7e83c25051d520133e56bfa86206352a285988e096bd14aaf5532a68ed0d100000000b5004830450221008f48ee3c6e69f8d2aeea9c482e3e80233fc83d78eb1ac7416362b25ae57d3eee02207f6b568f8f611efb17bd6bf8d0b32d334aa4110a2cc97a06f48aba4d045b7cd4014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653aeffffffff9643add957ab239b1d8fe387cc3807b48130a553a7b181e447ee9c089d82e2a600000000b40047304402206c5f93cbedc06ac1bae846d850a27c56b0e6f75ef247d3d67a10bbe8ea9da90302203d64f4803c0cbe5703268d58a80d54a3ad72cb1b856f19a6c6c999aad011a5b9014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c153aeffffffff02a0860100000000001976a91412e8391ad256dcdc023365978418d658dfecba1c88aca0860100000000001976a914f0a2b64e56ee2ff57126232f84af6e3a41d4055088ac00000000')

    # first internal, second external
    def test_internal_external(self):
        self.setup_mnemonic_nopin_nopassphrase()

        out1 = proto_types.TxOutputType(address_n=[4],
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        out2 = proto_types.TxOutputType(address='17kTB7qSk3MupQxWdiv5ZU3zcrZc2Azes1',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        with self.client:
            self.client.set_expected_responses(self._responses(self.inp1, self.inp2, change=1))
            (_, serialized_tx) = self.client.sign_tx('Bitcoin', [self.inp1, self.inp2, ], [out1, out2, ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000023da7e83c25051d520133e56bfa86206352a285988e096bd14aaf5532a68ed0d100000000b4004730440220740f305af9cd10f290b0d5dd27968d3c08f313d58e70feb260e076bd57d427bd02202c0296b38e82993983b971196589a2c74cdc4931a2da88aa2c2bd89e58a3fdb2014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653aeffffffff9643add957ab239b1d8fe387cc3807b48130a553a7b181e447ee9c089d82e2a600000000b400473044022042f53a8cd53762fb95113d11f56f050dab9dead9a2026807c728d5c42ed62e9902202e708162a50ca16f5fac082c1a2a5350fcb74cbfce39968e76300a36457f45a7014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c153aeffffffff02a0860100000000001976a914f0a2b64e56ee2ff57126232f84af6e3a41d4055088aca0860100000000001976a9144a087d89f8ad16ca029c675b037c02fd1c5f9aec88ac00000000')

    # both outputs are external
    def test_multisig_external_external(self):
        self.setup_mnemonic_nopin_nopassphrase()

        out1 = proto_types.TxOutputType(address='3796Q9jVirg2KY1WQRqtmHKXCoSk8MB7Td',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        out2 = proto_types.TxOutputType(address='3CTPCg3ksh59jWt9zQpTPHCSQDCdJoQQ9d',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        with self.client:
            self.client.set_expected_responses(self._responses(self.inp1, self.inp2))
            (_, serialized_tx) = self.client.sign_tx('Bitcoin', [self.inp1, self.inp2, ], [out1, out2, ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000023da7e83c25051d520133e56bfa86206352a285988e096bd14aaf5532a68ed0d100000000b500483045022100915e3761efb41895d40fa3bf8d3a68be7eb949e2411ec5655e231bbb334925ea02205814166b786a912f8f47315c9ede4955d2dfc70bb0b51230fccaaacf5a39a0ae014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653aeffffffff9643add957ab239b1d8fe387cc3807b48130a553a7b181e447ee9c089d82e2a600000000b400473044022018ca5516ee127eeeb8c70f10c267dd803b599688eade659e3b210bbf1712fffe02206c1adb35e672e67ee102dc232456ac5edc86f58f83d698995981e68d2a2a4294014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c153aeffffffff02a08601000000000017a9143bc72e27ec21644ace15b367ef7ba491f2507eb587a08601000000000017a9147615527d78854293edadf83682ea26937f8a51bb8700000000')

    # inputs match, change matches (first is change)
    def test_multisig_change_match_first(self):
        self.setup_mnemonic_nopin_nopassphrase()

        multisig_out1 = proto_types.MultisigRedeemScriptType(
                        pubkeys=[proto_types.HDNodePathType(node=self.node_int, address_n=[1]),
                                 proto_types.HDNodePathType(node=self.node_ext1, address_n=[1]),
                                 proto_types.HDNodePathType(node=self.node_ext2, address_n=[1])],
                        signatures=[b'', b'', b''],
                        m=2,
                        )

        out1 = proto_types.TxOutputType(address_n=[1],
                              multisig=multisig_out1,
                              amount=100000,
                              script_type=proto_types.PAYTOMULTISIG)

        out2 = proto_types.TxOutputType(address='3CTPCg3ksh59jWt9zQpTPHCSQDCdJoQQ9d',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        with self.client:
            self.client.set_expected_responses(self._responses(self.inp1, self.inp2, change=1))
            (_, serialized_tx) = self.client.sign_tx('Bitcoin', [self.inp1, self.inp2, ], [out1, out2, ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000023da7e83c25051d520133e56bfa86206352a285988e096bd14aaf5532a68ed0d100000000b40047304402203cb26eac850f590951b12b513a5369c0b301c6d3ae1cd251aa837ce35427bdec0220289834c8c5cb837351ae06498d77fa6707611c09d628864a1f0a7e1d381bddd8014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653aeffffffff9643add957ab239b1d8fe387cc3807b48130a553a7b181e447ee9c089d82e2a600000000b40047304402207c2e39254d1e9cff42b523bcc0bf5ab66ae0c584deb2413759d9b269b1fe9e6f02205bc93a1884625b2359247c15a57e4e80b184b21a5f95e7f5ce846323236e30ac014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c153aeffffffff02a08601000000000017a914b69a5c6a63c01a09a90eb690031963f737cf96ed87a08601000000000017a9147615527d78854293edadf83682ea26937f8a51bb8700000000')

    # inputs match, change matches (second is change)
    def test_multisig_change_match_second(self):
        self.setup_mnemonic_nopin_nopassphrase()

        multisig_out2 = proto_types.MultisigRedeemScriptType(
                        pubkeys=[proto_types.HDNodePathType(node=self.node_int, address_n=[2]),
                                 proto_types.HDNodePathType(node=self.node_ext1, address_n=[2]),
                                 proto_types.HDNodePathType(node=self.node_ext2, address_n=[2])],
                        signatures=[b'', b'', b''],
                        m=2,
                        )

        out1 = proto_types.TxOutputType(address='37Wf955dcCaFSJmiNaGpacczMwj7iC8JMx',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        out2 = proto_types.TxOutputType(address_n=[2],
                              multisig=multisig_out2,
                              amount=100000,
                              script_type=proto_types.PAYTOMULTISIG)

        with self.client:
            self.client.set_expected_responses(self._responses(self.inp1, self.inp2, change=2))
            (_, serialized_tx) = self.client.sign_tx('Bitcoin', [self.inp1, self.inp2, ], [out1, out2, ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000023da7e83c25051d520133e56bfa86206352a285988e096bd14aaf5532a68ed0d100000000b5004830450221008d5710ba7df3c32358a723c69458acc81a296646cad262217975ba00b24fdc6402201623a3e3778e6abad9025343cef6fad361a054463f928509324ee862a2e84e6a014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653aeffffffff9643add957ab239b1d8fe387cc3807b48130a553a7b181e447ee9c089d82e2a600000000b400473044022014d07e6a67c14a81d1042be2990d4c4ac29d9a46ba051168a9ccc09e987d97e202203cfe6714cff04421a90d5a4507f875515a1357fc2df306a44617ae7f88c7fcd1014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c153aeffffffff02a08601000000000017a9143fdb3ed6e85c87d77f263be3b0d0abc508fe4e3787a08601000000000017a914021809d0cb4a6fcf436e6b8cc743511b09d183218700000000')

    # inputs match, change mismatches (second is change)
    def test_multisig_mismatch_change(self):
        self.setup_mnemonic_nopin_nopassphrase()

        multisig_out2 = proto_types.MultisigRedeemScriptType(
                        pubkeys=[proto_types.HDNodePathType(node=self.node_int, address_n=[2]),
                                 proto_types.HDNodePathType(node=self.node_ext1, address_n=[2]),
                                 proto_types.HDNodePathType(node=self.node_ext3, address_n=[2])],
                        signatures=[b'', b'', b''],
                        m=2,
                        )

        out1 = proto_types.TxOutputType(address='3796Q9jVirg2KY1WQRqtmHKXCoSk8MB7Td',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        out2 = proto_types.TxOutputType(address_n=[2],
                              multisig=multisig_out2,
                              amount=100000,
                              script_type=proto_types.PAYTOMULTISIG)

        with self.client:
            self.client.set_expected_responses(self._responses(self.inp1, self.inp2))
            (_, serialized_tx) = self.client.sign_tx('Bitcoin', [self.inp1, self.inp2, ], [out1, out2, ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000023da7e83c25051d520133e56bfa86206352a285988e096bd14aaf5532a68ed0d100000000b40047304402202a6238e8c9955a3d01609cbdaafcf47b0a53b2eabe2e28cf942fe9e253457eba02207f67afb4c35a8d28603e71a0696d0c123c0ca2370d78076c692ca3036c0a2c35014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653aeffffffff9643add957ab239b1d8fe387cc3807b48130a553a7b181e447ee9c089d82e2a600000000b40047304402200e87ee683b27f3995a2f8c9e9b4b17e24399d43a4c69ce5402105b6b93ac63cf0220201ba91db1f4ca2768f9277c115e95c2297bbe40969dcf9d10d0836a75c8ac9c014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c153aeffffffff02a08601000000000017a9143bc72e27ec21644ace15b367ef7ba491f2507eb587a08601000000000017a9143f22da0a6d4a4341be319e48e7b51b5a113fda208700000000')

    # inputs mismatch, change matches with first input
    def test_multisig_mismatch_inputs(self):
        self.setup_mnemonic_nopin_nopassphrase()

        multisig_out1 = proto_types.MultisigRedeemScriptType(
                        pubkeys=[proto_types.HDNodePathType(node=self.node_ext1, address_n=[1]),
                                 proto_types.HDNodePathType(node=self.node_ext2, address_n=[1]),
                                 proto_types.HDNodePathType(node=self.node_int, address_n=[1])],
                        signatures=[b'', b'', b''],
                        m=2,
                        )

        out1 = proto_types.TxOutputType(address_n=[1],
                              multisig=multisig_out1,
                              amount=100000,
                              script_type=proto_types.PAYTOMULTISIG)

        out2 = proto_types.TxOutputType(address='3CTPCg3ksh59jWt9zQpTPHCSQDCdJoQQ9d',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        with self.client:
            self.client.set_expected_responses(self._responses(self.inp1, self.inp3))
            (_, serialized_tx) = self.client.sign_tx('Bitcoin', [self.inp1, self.inp3, ], [out1, out2, ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000023da7e83c25051d520133e56bfa86206352a285988e096bd14aaf5532a68ed0d100000000b40047304402204b7d6c7e9feef91209cbdf4deaf855696dc22a40e57bd3eafd5e00b0ee41d9de0220262c5a05d0b46ef98fddfef3831b3ebb6841ffbeb10666f8fb6f8d2e3023e30d014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653aeffffffffe39b254db8137202c7690cb0c6738f2e61661ce16f92b3f2087a00e5e51abce401000000b500483045022100bb2118da21c8a84f115b655f640f269a40be77ae2c0af9c5ffd8260a85dbfc7702202e7b5b6c05b8f50bd879dbee88828e80e85448d686b63a1a50e99d921923f6f5014c69522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e2102e0c21e2a7cf00b94c5421725acff97f9826598b91f2340c5ddda730caca7d648210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653aeffffffff02a08601000000000017a914a4efc33d43d7a8a0040182c76ab624ff862f50d287a08601000000000017a9147615527d78854293edadf83682ea26937f8a51bb8700000000')

if __name__ == '__main__':
    unittest.main()
