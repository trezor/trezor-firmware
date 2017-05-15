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

from trezorlib import messages_pb2 as proto
from trezorlib import types_pb2 as proto_types


TXHASH_d5f65e = binascii.unhexlify(b'd5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')


class TestProtectionLevels(common.TrezorTest):

    def test_initialize(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.Features()])
            self.client.init_device()

    def test_apply_settings(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.PinMatrixRequest(),
                                      proto.ButtonRequest(),
                                      proto.Success(),
                                      proto.Features()])  # TrezorClient reinitializes device
            self.client.apply_settings(label='nazdar')

    def test_change_pin(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.ButtonRequest(),
                                      proto.PinMatrixRequest(),
                                      proto.PinMatrixRequest(),
                                      proto.PinMatrixRequest(),
                                      proto.Success(),
                                      proto.Features()])
            self.client.change_pin()

    def test_ping(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.ButtonRequest(),
                                      proto.PinMatrixRequest(),
                                      proto.PassphraseRequest(),
                                      proto.Success()])
            self.client.ping('msg', True, True, True)

    def test_get_entropy(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.ButtonRequest(),
                                      proto.Entropy()])
            self.client.get_entropy(10)

    def test_get_public_key(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.PinMatrixRequest(),
                                      proto.PassphraseRequest(),
                                      proto.PublicKey()])
            self.client.get_public_node([])

    def test_get_address(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.PinMatrixRequest(),
                                      proto.PassphraseRequest(),
                                      proto.Address()])
            self.client.get_address('Bitcoin', [])

    def test_wipe_device(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.ButtonRequest(),
                                      proto.Success(),
                                      proto.Features()])
            self.client.wipe_device()

    def test_load_device(self):
        with self.client:
            self.client.set_expected_responses([proto.ButtonRequest(),
                                                proto.Success(),
                                                proto.Features()])
            self.client.load_device_by_mnemonic('this is mnemonic', '1234', True, 'label', 'english', skip_checksum=True)

        # This must fail, because device is already initialized
        self.assertRaises(Exception, self.client.load_device_by_mnemonic,
                          'this is mnemonic', '1234', True, 'label', 'english', skip_checksum=True)

    def test_reset_device(self):
        with self.client:
            self.client.set_expected_responses([proto.EntropyRequest()] + \
                                     [proto.ButtonRequest()] * 24 + \
                                     [proto.Success(),
                                      proto.Features()])
            self.client.reset_device(False, 128, True, False, 'label', 'english')

        # This must fail, because device is already initialized
        self.assertRaises(Exception, self.client.reset_device, False, 128, True, False, 'label', 'english')

    def test_recovery_device(self):
        with self.client:
            self.client.set_mnemonic(self.mnemonic12)
            self.client.set_expected_responses([proto.WordRequest()] * 24 + \
                                     [proto.Success(),
                                      proto.Features()])
            self.client.recovery_device(12, False, False, 'label', 'english')

        # This must fail, because device is already initialized
        self.assertRaises(Exception, self.client.recovery_device, 12, False, False, 'label', 'english')

    def test_sign_message(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.ButtonRequest(),
                                      proto.PinMatrixRequest(),
                                      proto.PassphraseRequest(),
                                      proto.MessageSignature()])
            self.client.sign_message('Bitcoin', [], 'testing message')

    def test_verify_message(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.ButtonRequest(),proto.Success()])
            self.client.verify_message(
                'Bitcoin',
                '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e',
                binascii.unhexlify(b'209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80'),
                'This is an example of a signed message.')

    def test_estimate_txsize(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.TxSize()])
            self.client.estimate_tx_size('Bitcoin', [], [])

    """
    def test_simplesigntx(self):
        self.setup_mnemonic_pin_passphrase()

        inp1 = proto_types.TxInputType(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                             prev_hash=TXHASH_d5f65e,
                             prev_index=0,
                             )

        out1 = proto_types.TxOutputType(address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
                              amount=390000 - 10000,
                              script_type=proto_types.PAYTOADDRESS,
                              )

        with self.client:
            self.client.set_expected_responses([proto.PinMatrixRequest(),
                                                proto.PassphraseRequest(),
                                                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                                                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                                                proto.TxRequest(request_type=proto_types.TXFINISHED)])
            self.client.simple_sign_tx('Bitcoin', [inp1, ], [out1, ])
    """

    def test_signtx(self):
        self.setup_mnemonic_pin_passphrase()

        inp1 = proto_types.TxInputType(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                             prev_hash=TXHASH_d5f65e,
                             prev_index=0,
                             )

        out1 = proto_types.TxOutputType(address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
                              amount=390000 - 10000,
                              script_type=proto_types.PAYTOADDRESS,
                              )

        with self.client:

            self.client.set_expected_responses([
                proto.PinMatrixRequest(),
                proto.PassphraseRequest(),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXMETA, details=proto_types.TxRequestDetailsType(tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            self.client.sign_tx('Bitcoin', [inp1, ], [out1, ])

    # def test_firmware_erase(self):
    #    pass

    # def test_firmware_upload(self):
    #    pass

if __name__ == '__main__':
    unittest.main()
