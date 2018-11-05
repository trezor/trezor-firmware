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

import pytest

from trezorlib import btc, debuglink, device, messages as proto, misc

from ..support.tx_cache import tx_cache
from .common import TrezorTest

TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)


@pytest.mark.skip_t2
class TestProtectionLevels(TrezorTest):
    def test_initialize(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.Features()])
            self.client.init_device()

    def test_apply_settings(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses(
                [
                    proto.PinMatrixRequest(),
                    proto.ButtonRequest(),
                    proto.Success(),
                    proto.Features(),
                ]
            )  # TrezorClient reinitializes device
            device.apply_settings(self.client, label="nazdar")

    def test_change_pin(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(),
                    proto.PinMatrixRequest(),
                    proto.PinMatrixRequest(),
                    proto.PinMatrixRequest(),
                    proto.Success(),
                    proto.Features(),
                ]
            )
            device.change_pin(self.client)

    def test_ping(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(),
                    proto.PinMatrixRequest(),
                    proto.PassphraseRequest(),
                    proto.Success(),
                ]
            )
            self.client.ping("msg", True, True, True)

    def test_get_entropy(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses([proto.ButtonRequest(), proto.Entropy()])
            misc.get_entropy(self.client, 10)

    def test_get_public_key(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses(
                [proto.PinMatrixRequest(), proto.PassphraseRequest(), proto.PublicKey()]
            )
            btc.get_public_node(self.client, [])

    def test_get_address(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses(
                [proto.PinMatrixRequest(), proto.PassphraseRequest(), proto.Address()]
            )
            btc.get_address(self.client, "Bitcoin", [])

    def test_wipe_device(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses(
                [proto.ButtonRequest(), proto.Success(), proto.Features()]
            )
            device.wipe(self.client)

    def test_load_device(self):
        with self.client:
            self.client.set_expected_responses(
                [proto.ButtonRequest(), proto.Success(), proto.Features()]
            )
            debuglink.load_device_by_mnemonic(
                self.client,
                "this is mnemonic",
                "1234",
                True,
                "label",
                "english",
                skip_checksum=True,
            )

        # This must fail, because device is already initialized
        with pytest.raises(Exception):
            debuglink.load_device_by_mnemonic(
                self.client,
                "this is mnemonic",
                "1234",
                True,
                "label",
                "english",
                skip_checksum=True,
            )

    def test_reset_device(self):
        with self.client:
            self.client.set_expected_responses(
                [proto.ButtonRequest()]
                + [proto.EntropyRequest()]
                + [proto.ButtonRequest()] * 24
                + [proto.Success(), proto.Features()]
            )
            device.reset(self.client, False, 128, True, False, "label", "english")

        # This must fail, because device is already initialized
        with pytest.raises(Exception):
            device.reset(self.client, False, 128, True, False, "label", "english")

    def test_recovery_device(self):
        self.client.set_mnemonic(self.mnemonic12)
        with self.client:
            self.client.set_expected_responses(
                [proto.ButtonRequest()]
                + [proto.WordRequest()] * 24
                + [proto.Success(), proto.Features()]
            )

            device.recover(
                self.client,
                12,
                False,
                False,
                "label",
                "english",
                self.client.mnemonic_callback,
            )

        # This must fail, because device is already initialized
        with pytest.raises(RuntimeError):
            device.recover(
                self.client,
                12,
                False,
                False,
                "label",
                "english",
                self.client.mnemonic_callback,
            )

    def test_sign_message(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(),
                    proto.PinMatrixRequest(),
                    proto.PassphraseRequest(),
                    proto.MessageSignature(),
                ]
            )
            btc.sign_message(self.client, "Bitcoin", [], "testing message")

    def test_verify_message(self):
        with self.client:
            self.setup_mnemonic_pin_passphrase()
            self.client.set_expected_responses(
                [proto.ButtonRequest(), proto.ButtonRequest(), proto.Success()]
            )
            btc.verify_message(
                self.client,
                "Bitcoin",
                "14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e",
                bytes.fromhex(
                    "209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
                ),
                "This is an example of a signed message.",
            )

    def test_signtx(self):
        self.setup_mnemonic_pin_passphrase()

        inp1 = proto.TxInputType(
            address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=390000 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:

            self.client.set_expected_responses(
                [
                    proto.PinMatrixRequest(),
                    proto.PassphraseRequest(),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=TXHASH_d5f65e),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=TXHASH_d5f65e
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=1, tx_hash=TXHASH_d5f65e
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            request_index=0, tx_hash=TXHASH_d5f65e
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            btc.sign_tx(
                self.client, "Bitcoin", [inp1], [out1], prev_txes=tx_cache("Bitcoin")
            )

    # def test_firmware_erase(self):
    #    pass

    # def test_firmware_upload(self):
    #    pass
