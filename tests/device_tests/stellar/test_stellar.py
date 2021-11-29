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

# XDR decoding tool available at:
#   https://www.stellar.org/laboratory/#xdr-viewer
#
# ## Test Info
#
# The default mnemonic generates the following Stellar keypair at path 44'/148'/0':
#   GAXSFOOGF4ELO5HT5PTN23T5XE6D5QWL3YBHSVQ2HWOFEJNYYMRJENBV
#   SDK6NSLLKX5UE3DSXGK56MEMTZBOJ6XT3LLA33BEAZUYGO6TXMHNRUPB
#
# ### Testing a new Operation
#
# 1. Start at the Stellar transaction builder: https://www.stellar.org/laboratory/#txbuilder?network=test
#   (Verify that the "test" network is active in the upper right)
#
# 2. Fill out the fields at the top as you like. We use mostly these values:
#   Source account: GAXSFOOGF4ELO5HT5PTN23T5XE6D5QWL3YBHSVQ2HWOFEJNYYMRJENBV
#   Transaction sequence number: 1000
#   Base fee: 100
#   Memo: None
#   Time Bounds: 461535181, 1575234180
#
# 3. Select the operation to test, such as Create Account
#
# 4. Fill out the fields for the operation
#
# 5. Scroll down to the bottom of the page and click "Sign in Transaction Signer"
#
# 6. Copy the generated XDR and add it as an "xdr" field to your test case
#
# 7. In the first "Add Signer" text box enter the secret key: SDK6NSLLKX5UE3DSXGK56MEMTZBOJ6XT3LLA33BEAZUYGO6TXMHNRUPB
#
# 8. Scroll down to the signed XDR blob and click "View in XDR Viewer"
#
# 9. Scroll down to the bottom and look at the "signatures" section. The Trezor should generate the same signature
#

from base64 import b64encode

import pytest

from trezorlib import messages, protobuf, stellar
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures


def parameters_to_proto(parameters):
    tx_data = parameters["tx"]
    ops_data = parameters["operations"]

    tx_data["address_n"] = parse_path(parameters["address_n"])
    tx_data["network_passphrase"] = parameters["network_passphrase"]
    tx_data["num_operations"] = len(ops_data)

    def make_op(operation_data):
        type_name = operation_data["_message_type"]
        assert type_name.startswith("Stellar") and type_name.endswith("Op")
        cls = getattr(messages, type_name)
        return protobuf.dict_to_proto(cls, operation_data)

    tx = protobuf.dict_to_proto(messages.StellarSignTx, tx_data)
    operations = [make_op(op) for op in ops_data]
    return tx, operations


@pytest.mark.altcoin
@pytest.mark.stellar
@parametrize_using_common_fixtures("stellar/sign_tx.json")
def test_sign_tx(client, parameters, result):
    tx, operations = parameters_to_proto(parameters)
    response = stellar.sign_tx(
        client, tx, operations, tx.address_n, tx.network_passphrase
    )
    assert response.public_key.hex() == result["public_key"]
    assert b64encode(response.signature).decode() == result["signature"]


@pytest.mark.altcoin
@pytest.mark.stellar
@parametrize_using_common_fixtures("stellar/sign_tx.json")
@pytest.mark.skipif(not stellar.HAVE_STELLAR_SDK, reason="requires Stellar SDK")
def test_xdr(parameters, result):
    from stellar_sdk import TransactionEnvelope

    envelope = TransactionEnvelope.from_xdr(
        parameters["xdr"], parameters["network_passphrase"]
    )
    tx, operations = stellar.from_envelope(envelope)
    tx.address_n = parse_path(parameters["address_n"])
    tx_expected, operations_expected = parameters_to_proto(parameters)
    assert tx == tx_expected
    for expected, actual in zip(operations_expected, operations):
        assert expected == actual


@pytest.mark.altcoin
@pytest.mark.stellar
@parametrize_using_common_fixtures("stellar/get_address.json")
def test_get_address(client, parameters, result):
    address_n = parse_path(parameters["path"])
    address = stellar.get_address(client, address_n, show_display=True)
    assert address == result["address"]
