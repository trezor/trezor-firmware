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

from trezorlib import btc, debuglink, device, messages as proto, misc
from trezorlib.exceptions import TrezorFailure

from ..common import MNEMONIC12
from ..tx_cache import tx_cache

TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)


@pytest.mark.skip_t2
class TestProtectionLevels:
    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_initialize(self, client):
        with client:
            client.set_expected_responses([proto.Features()])
            client.init_device()

    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_apply_settings(self, client):
        with client:
            client.set_expected_responses(
                [
                    proto.PinMatrixRequest(),
                    proto.ButtonRequest(),
                    proto.Success(),
                    proto.Features(),
                ]
            )  # TrezorClient reinitializes device
            device.apply_settings(client, label="nazdar")

    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_change_pin(self, client):
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(),
                    proto.PinMatrixRequest(),
                    proto.PinMatrixRequest(),
                    proto.PinMatrixRequest(),
                    proto.Success(),
                    proto.Features(),
                ]
            )
            device.change_pin(client)

    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_ping(self, client):
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(),
                    proto.PinMatrixRequest(),
                    proto.PassphraseRequest(),
                    proto.Success(),
                ]
            )
            client.ping("msg", True, True, True)

    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_get_entropy(self, client):
        with client:
            client.set_expected_responses([proto.ButtonRequest(), proto.Entropy()])
            misc.get_entropy(client, 10)

    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_get_public_key(self, client):
        with client:
            client.set_expected_responses(
                [proto.PinMatrixRequest(), proto.PassphraseRequest(), proto.PublicKey()]
            )
            btc.get_public_node(client, [])

    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_get_address(self, client):
        with client:
            client.set_expected_responses(
                [proto.PinMatrixRequest(), proto.PassphraseRequest(), proto.Address()]
            )
            btc.get_address(client, "Bitcoin", [])

    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_wipe_device(self, client):
        with client:
            client.set_expected_responses(
                [proto.ButtonRequest(), proto.Success(), proto.Features()]
            )
            device.wipe(client)

    @pytest.mark.setup_client(uninitialized=True)
    def test_load_device(self, client):
        with client:
            client.set_expected_responses(
                [proto.ButtonRequest(), proto.Success(), proto.Features()]
            )
            debuglink.load_device_by_mnemonic(
                client,
                "this is mnemonic",
                "1234",
                True,
                "label",
                "english",
                skip_checksum=True,
            )

        with pytest.raises(TrezorFailure):
            # This must fail, because device is already initialized
            # Using direct call because `load_device_by_mnemonic` has its own check
            client.call(
                proto.LoadDevice(
                    mnemonics="this is mnemonic",
                    pin="1234",
                    passphrase_protection=True,
                    language="english",
                    label="label",
                    skip_checksum=True,
                )
            )

    @pytest.mark.setup_client(uninitialized=True)
    def test_reset_device(self, client):
        with client:
            client.set_expected_responses(
                [proto.ButtonRequest()]
                + [proto.EntropyRequest()]
                + [proto.ButtonRequest()] * 24
                + [proto.Success(), proto.Features()]
            )
            device.reset(client, False, 128, True, False, "label", "english")

        with pytest.raises(TrezorFailure):
            # This must fail, because device is already initialized
            # Using direct call because `device.reset` has its own check
            client.call(
                proto.ResetDevice(
                    display_random=False,
                    strength=128,
                    passphrase_protection=True,
                    pin_protection=False,
                    label="label",
                    language="english",
                )
            )

    @pytest.mark.setup_client(uninitialized=True)
    def test_recovery_device(self, client):
        client.set_mnemonic(MNEMONIC12)
        with client:
            client.set_expected_responses(
                [proto.ButtonRequest()]
                + [proto.WordRequest()] * 24
                + [proto.Success(), proto.Features()]
            )

            device.recover(
                client, 12, False, False, "label", "english", client.mnemonic_callback
            )

        with pytest.raises(TrezorFailure):
            # This must fail, because device is already initialized
            # Using direct call because `device.reset` has its own check
            client.call(
                proto.RecoveryDevice(
                    word_count=12,
                    passphrase_protection=False,
                    pin_protection=False,
                    label="label",
                    language="english",
                )
            )

    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_sign_message(self, client):
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(),
                    proto.PinMatrixRequest(),
                    proto.PassphraseRequest(),
                    proto.MessageSignature(),
                ]
            )
            btc.sign_message(client, "Bitcoin", [], "testing message")

    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_verify_message(self, client):
        with client:
            client.set_expected_responses(
                [proto.ButtonRequest(), proto.ButtonRequest(), proto.Success()]
            )
            btc.verify_message(
                client,
                "Bitcoin",
                "14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e",
                bytes.fromhex(
                    "209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
                ),
                "This is an example of a signed message.",
            )

    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_signtx(self, client):
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

        with client:

            client.set_expected_responses(
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
                client, "Bitcoin", [inp1], [out1], prev_txes=tx_cache("Bitcoin")
            )

    # def test_firmware_erase(self):
    #    pass

    # def test_firmware_upload(self):
    #    pass

    @pytest.mark.setup_client(pin=True)
    def test_pin_cached(self, client):
        assert client.features.pin_cached is False

        with client:
            client.set_expected_responses(
                [proto.ButtonRequest(), proto.PinMatrixRequest(), proto.Success()]
            )
            client.ping("msg", True, True, True)

        client.init_device()
        assert client.features.pin_cached is True
        with client:
            client.set_expected_responses([proto.ButtonRequest(), proto.Success()])
            client.ping("msg", True, True, True)

    @pytest.mark.setup_client(passphrase=True)
    def test_passphrase_cached(self, client):
        assert client.features.passphrase_cached is False

        with client:
            client.set_expected_responses(
                [proto.ButtonRequest(), proto.PassphraseRequest(), proto.Success()]
            )
            client.ping("msg", True, True, True)

        features = client.call(proto.GetFeatures())
        assert features.passphrase_cached is True
        with client:
            client.set_expected_responses([proto.ButtonRequest(), proto.Success()])
            client.ping("msg", True, True, True)
