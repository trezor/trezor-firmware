# This file is part of the Trezor project.
#
# Copyright (C) 2012-2021 SatoshiLabs and contributors
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
from stellar_sdk import Account, Asset, Network, TransactionBuilder, TrustLineEntryFlag
from stellar_sdk.strkey import StrKey

from trezorlib import messages, stellar


def test_stellar_parse_operation_simple_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
            v1=False,
        )
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_NONE
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash is None
    assert len(parsed_operations) == 1


def test_stellar_parse_transaction_memo_text_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    memo_text = b"Have a nice day!"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
            v1=False,
        )
        .add_text_memo(memo_text=memo_text)
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_TEXT
    assert parsed_tx.memo_text == memo_text.decode("utf-8")
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash is None
    assert len(parsed_operations) == 1


def test_stellar_parse_transaction_bytes_memo_id_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    memo_id = 123456789
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
            v1=False,
        )
        .add_id_memo(memo_id)
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_ID
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id == memo_id
    assert parsed_tx.memo_hash is None
    assert len(parsed_operations) == 1


def test_stellar_parse_transaction_memo_hash_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    memo_hash = "b77cd735095e1b58da2d7415c1f51f423a722b34d7d5002d8896608a9130a74b"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
            v1=False,
        )
        .add_hash_memo(memo_hash)
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_HASH
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash.hex() == memo_hash
    assert len(parsed_operations) == 1


def test_stellar_parse_transaction_memo_return_hash_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    memo_return = "b77cd735095e1b58da2d7415c1f51f423a722b34d7d5002d8896608a9130a74b"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
            v1=False,
        )
        .add_return_hash_memo(memo_return)
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_RETURN
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash.hex() == memo_return
    assert len(parsed_operations) == 1


def test_stellar_parse_transaction_time_bounds_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    min_time = 1628089098
    max_time = 1628090000
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
            v1=False,
        )
        .add_time_bounds(min_time=min_time, max_time=max_time)
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start == min_time
    assert parsed_tx.timebounds_end == max_time
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_NONE
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash is None
    assert len(parsed_operations) == 1


def test_stellar_parse_operation_multiple_operations_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    base_fee = 200
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    operation1_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "XLM"
    asset_issuer = None
    operation2_source = "GBHWKBPP3O4H2BUUKSFXE4PK5WHLQYVZIZUNUJ4AU5VUZZEVBDMXISAS"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
            v1=False,
        )
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation1_source
        )
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation2_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_NONE
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash is None
    assert len(parsed_operations) == 2
    assert isinstance(parsed_operations[0], messages.StellarManageDataOp)
    assert parsed_operations[0].source_account == operation1_source
    assert parsed_operations[0].key == data_name
    assert parsed_operations[0].value == data_value
    assert isinstance(parsed_operations[1], messages.StellarPaymentOp)
    assert parsed_operations[1].source_account == operation2_source
    assert parsed_operations[1].destination_account == destination
    assert parsed_operations[1].asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operations[1].asset.code is None
    assert parsed_operations[1].asset.issuer is None
    assert parsed_operations[1].amount == 500111000


def test_stellar_parse_operation_create_account_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    starting_balance = "100.0333"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_create_account_op(
            destination=destination,
            starting_balance=starting_balance,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarCreateAccountOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.new_account == destination
    assert parsed_operation.starting_balance == 1000333000


def test_stellar_parse_operation_payment_native_asset_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "XLM"
    asset_issuer = None
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarPaymentOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination
    assert parsed_operation.asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.asset.code is None
    assert parsed_operation.asset.issuer is None
    assert parsed_operation.amount == 500111000


def test_stellar_parse_operation_payment_alpha4_asset_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "USD"
    asset_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarPaymentOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination
    assert parsed_operation.asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.asset.code == asset_code
    assert parsed_operation.asset.issuer == asset_issuer
    assert parsed_operation.amount == 500111000


def test_stellar_parse_operation_payment_alpha12_asset_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "BANANA"
    asset_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarPaymentOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination
    assert parsed_operation.asset.type == stellar.ASSET_TYPE_ALPHA12
    assert parsed_operation.asset.code == asset_code
    assert parsed_operation.asset.issuer == asset_issuer
    assert parsed_operation.amount == 500111000


def test_stellar_parse_operation_path_payment_strict_receive_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    send_max = "50.0111"
    dest_amount = "100"
    send_code = "XLM"
    send_issuer = None
    dest_code = "USD"
    dest_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    path_asset1 = Asset(
        "JPY", "GD6PV7DXQJX7AGVXFQ2MTCLTCH6LR3E6IO2EO2YDZD7F7IOZZCCB5DSQ"
    )
    path_asset2 = Asset(
        "BANANA", "GC7EKO37HNSKQ3V6RZ274EO7SFOWASQRHLX3OR5FIZK6UMV6LIEDXHGZ"
    )

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_path_payment_strict_receive_op(
            destination=destination,
            send_code=send_code,
            send_issuer=send_issuer,
            send_max=send_max,
            dest_code=dest_code,
            dest_issuer=dest_issuer,
            dest_amount=dest_amount,
            path=[path_asset1, path_asset2],
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]

    assert isinstance(parsed_operation, messages.StellarPathPaymentOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination
    assert parsed_operation.send_asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.send_max == 500111000
    assert parsed_operation.destination_asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.destination_asset.code == dest_code
    assert parsed_operation.destination_asset.issuer == dest_issuer
    assert len(parsed_operation.paths) == 2
    assert parsed_operation.paths[0].type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.paths[0].code == path_asset1.code
    assert parsed_operation.paths[0].issuer == path_asset1.issuer
    assert parsed_operation.paths[1].type == stellar.ASSET_TYPE_ALPHA12
    assert parsed_operation.paths[1].code == path_asset2.code
    assert parsed_operation.paths[1].issuer == path_asset2.issuer


def test_stellar_parse_operation_path_payment_strict_receive_empty_path_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    send_max = "50.0111"
    dest_amount = "100"
    send_code = "XLM"
    send_issuer = None
    dest_code = "USD"
    dest_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_path_payment_strict_receive_op(
            destination=destination,
            send_code=send_code,
            send_issuer=send_issuer,
            send_max=send_max,
            dest_code=dest_code,
            dest_issuer=dest_issuer,
            dest_amount=dest_amount,
            path=[],
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarPathPaymentOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination
    assert parsed_operation.send_asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.send_max == 500111000
    assert parsed_operation.destination_asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.destination_asset.code == dest_code
    assert parsed_operation.destination_asset.issuer == dest_issuer
    assert len(parsed_operation.paths) == 0


def test_stellar_parse_operation_manage_sell_offer_new_offer_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_manage_sell_offer_op(
            selling_code=selling_code,
            selling_issuer=selling_issuer,
            buying_code=buying_code,
            buying_issuer=buying_issuer,
            amount=amount,
            price=price,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarManageOfferOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.selling_asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.buying_asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.buying_asset.code == buying_code
    assert parsed_operation.buying_asset.issuer == buying_issuer
    assert parsed_operation.amount == 500111000
    assert parsed_operation.price_n == 1
    assert parsed_operation.price_d == 2
    assert parsed_operation.offer_id == 0  # indicates a new offer


def test_stellar_parse_operation_manage_sell_offer_update_offer_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    offer_id = 12345
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_manage_sell_offer_op(
            selling_code=selling_code,
            selling_issuer=selling_issuer,
            buying_code=buying_code,
            buying_issuer=buying_issuer,
            amount=amount,
            price=price,
            offer_id=offer_id,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarManageOfferOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.selling_asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.buying_asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.buying_asset.code == buying_code
    assert parsed_operation.buying_asset.issuer == buying_issuer
    assert parsed_operation.amount == 500111000
    assert parsed_operation.price_n == 1
    assert parsed_operation.price_d == 2
    assert parsed_operation.offer_id == offer_id


def test_stellar_parse_operation_create_passive_sell_offer_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_create_passive_sell_offer_op(
            selling_code=selling_code,
            selling_issuer=selling_issuer,
            buying_code=buying_code,
            buying_issuer=buying_issuer,
            amount=amount,
            price=price,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarCreatePassiveOfferOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.selling_asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.buying_asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.buying_asset.code == buying_code
    assert parsed_operation.buying_asset.issuer == buying_issuer
    assert parsed_operation.amount == 500111000
    assert parsed_operation.price_n == 1
    assert parsed_operation.price_d == 2


def test_stellar_parse_operation_set_options_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    inflation_dest = "GAXN7HZQTHIPW7N2HGPAXMR42LPJ5VLYXMCCOX4D3JC4CQZGID3UYUPF"
    clear_flags = 1
    set_flags = 6
    master_weight = 255
    low_threshold = 10
    med_threshold = 20
    high_threshold = 30
    home_domain = "example.com"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_set_options_op(
            inflation_dest=inflation_dest,
            clear_flags=clear_flags,
            set_flags=set_flags,
            master_weight=master_weight,
            low_threshold=low_threshold,
            med_threshold=med_threshold,
            high_threshold=high_threshold,
            home_domain=home_domain,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarSetOptionsOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.inflation_destination_account == inflation_dest
    assert parsed_operation.clear_flags == clear_flags
    assert parsed_operation.set_flags == set_flags
    assert parsed_operation.master_weight == master_weight
    assert parsed_operation.low_threshold == low_threshold
    assert parsed_operation.medium_threshold == med_threshold
    assert parsed_operation.high_threshold == high_threshold
    assert parsed_operation.home_domain == home_domain
    assert parsed_operation.signer_type is None
    assert parsed_operation.signer_key is None
    assert parsed_operation.signer_weight is None


def test_stellar_parse_operation_set_options_ed25519_signer_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    signer = "GAXN7HZQTHIPW7N2HGPAXMR42LPJ5VLYXMCCOX4D3JC4CQZGID3UYUPF"
    weight = 10
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_ed25519_public_key_signer(
            account_id=signer, weight=weight, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarSetOptionsOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.inflation_destination_account is None
    assert parsed_operation.clear_flags is None
    assert parsed_operation.set_flags is None
    assert parsed_operation.master_weight is None
    assert parsed_operation.low_threshold is None
    assert parsed_operation.medium_threshold is None
    assert parsed_operation.high_threshold is None
    assert parsed_operation.home_domain is None
    assert parsed_operation.signer_type == 0
    assert parsed_operation.signer_key == StrKey.decode_ed25519_public_key(signer)
    assert parsed_operation.signer_weight == weight


def test_stellar_parse_operation_set_options_pre_auth_tx_signer_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    signer = bytes.fromhex(
        "2db4b22ca018119c5027a80578813ffcf582cda4aa9e31cd92b43cfa4fc5a000"
    )
    weight = 30
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_pre_auth_tx_signer(
            pre_auth_tx_hash=signer, weight=weight, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarSetOptionsOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.inflation_destination_account is None
    assert parsed_operation.clear_flags is None
    assert parsed_operation.set_flags is None
    assert parsed_operation.master_weight is None
    assert parsed_operation.low_threshold is None
    assert parsed_operation.medium_threshold is None
    assert parsed_operation.high_threshold is None
    assert parsed_operation.home_domain is None
    assert parsed_operation.signer_type == 1
    assert parsed_operation.signer_key == signer
    assert parsed_operation.signer_weight == weight


def test_stellar_parse_operation_set_options_hashx_signer_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    signer = bytes.fromhex(
        "3389e9f0f1a65f19736cacf544c2e825313e8447f569233bb8db39aa607c8000"
    )
    weight = 20
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_hashx_signer(sha256_hash=signer, weight=weight, source=operation_source)
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarSetOptionsOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.inflation_destination_account is None
    assert parsed_operation.clear_flags is None
    assert parsed_operation.set_flags is None
    assert parsed_operation.master_weight is None
    assert parsed_operation.low_threshold is None
    assert parsed_operation.medium_threshold is None
    assert parsed_operation.high_threshold is None
    assert parsed_operation.home_domain is None
    assert parsed_operation.signer_type == 2
    assert parsed_operation.signer_key == signer
    assert parsed_operation.signer_weight == weight


def test_stellar_parse_operation_change_trust_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    asset_code = "USD"
    asset_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    limit = "1000"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_change_trust_op(
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            limit=limit,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarChangeTrustOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.asset.code == asset_code
    assert parsed_operation.asset.issuer == asset_issuer
    assert parsed_operation.limit == 10000000000


def test_stellar_parse_operation_allow_trust_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    asset_code = "USD"
    trustor = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_allow_trust_op(
            trustor=trustor,
            asset_code=asset_code,
            authorize=TrustLineEntryFlag.AUTHORIZED_FLAG,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarAllowTrustOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.asset_type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.asset_code == asset_code
    assert parsed_operation.trusted_account == trustor
    assert parsed_operation.is_authorized == TrustLineEntryFlag.AUTHORIZED_FLAG.value


def test_stellar_parse_operation_allow_trust_unsupport_flag_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    asset_code = "USD"
    trustor = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_allow_trust_op(
            trustor=trustor,
            asset_code=asset_code,
            authorize=TrustLineEntryFlag.AUTHORIZED_TO_MAINTAIN_LIABILITIES_FLAG,
            source=operation_source,
        )
        .build()
    )

    with pytest.raises(ValueError, match="Unsupported trust line flag"):
        stellar.from_envelope(envelope)


def test_stellar_parse_operation_account_merge_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_account_merge_op(destination=destination, source=operation_source)
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarAccountMergeOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination


def test_stellar_parse_operation_manage_data_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarManageDataOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.key == data_name
    assert parsed_operation.value == data_value


def test_stellar_parse_operation_manage_data_remove_data_entity_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = None  # remove data entity
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarManageDataOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.key == data_name
    assert parsed_operation.value is None


def test_stellar_parse_operation_bump_sequence_v0():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    bump_to = 143487250972278900
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=False,
        )
        .append_bump_sequence_op(bump_to=bump_to, source=operation_source)
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarBumpSequenceOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.bump_to == bump_to


def test_stellar_parse_operation_simple_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
        )
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_NONE
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash is None
    assert len(parsed_operations) == 1


def test_stellar_parse_transaction_memo_text_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    memo_text = b"Have a nice day!"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
        )
        .add_text_memo(memo_text=memo_text)
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_TEXT
    assert parsed_tx.memo_text == memo_text.decode("utf-8")
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash is None
    assert len(parsed_operations) == 1


def test_stellar_parse_transaction_bytes_memo_id_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    memo_id = 123456789
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
        )
        .add_id_memo(memo_id)
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_ID
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id == memo_id
    assert parsed_tx.memo_hash is None
    assert len(parsed_operations) == 1


def test_stellar_parse_transaction_memo_hash_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    memo_hash = "b77cd735095e1b58da2d7415c1f51f423a722b34d7d5002d8896608a9130a74b"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
        )
        .add_hash_memo(memo_hash)
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_HASH
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash.hex() == memo_hash
    assert len(parsed_operations) == 1


def test_stellar_parse_transaction_memo_return_hash_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    memo_return = "b77cd735095e1b58da2d7415c1f51f423a722b34d7d5002d8896608a9130a74b"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
        )
        .add_return_hash_memo(memo_return)
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_RETURN
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash.hex() == memo_return
    assert len(parsed_operations) == 1


def test_stellar_parse_transaction_time_bounds_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    min_time = 1628089098
    max_time = 1628090000
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    base_fee = 200

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
            v1=False,
        )
        .add_time_bounds(min_time=min_time, max_time=max_time)
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start == min_time
    assert parsed_tx.timebounds_end == max_time
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_NONE
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash is None
    assert len(parsed_operations) == 1


def test_stellar_parse_operation_multiple_operations_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    base_fee = 200
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    operation1_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "XLM"
    asset_issuer = None
    operation2_source = "GBHWKBPP3O4H2BUUKSFXE4PK5WHLQYVZIZUNUJ4AU5VUZZEVBDMXISAS"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
        )
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation1_source
        )
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation2_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert parsed_tx.source_account == tx_source
    assert parsed_tx.fee == envelope.transaction.fee
    assert parsed_tx.sequence_number == sequence + 1
    assert parsed_tx.timebounds_start is None
    assert parsed_tx.timebounds_end is None
    assert parsed_tx.memo_type == stellar.MEMO_TYPE_NONE
    assert parsed_tx.memo_text is None
    assert parsed_tx.memo_id is None
    assert parsed_tx.memo_hash is None
    assert len(parsed_operations) == 2
    assert isinstance(parsed_operations[0], messages.StellarManageDataOp)
    assert parsed_operations[0].source_account == operation1_source
    assert parsed_operations[0].key == data_name
    assert parsed_operations[0].value == data_value
    assert isinstance(parsed_operations[1], messages.StellarPaymentOp)
    assert parsed_operations[1].source_account == operation2_source
    assert parsed_operations[1].destination_account == destination
    assert parsed_operations[1].asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operations[1].asset.code is None
    assert parsed_operations[1].asset.issuer is None
    assert parsed_operations[1].amount == 500111000


def test_stellar_parse_operation_create_account_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    starting_balance = "100.0333"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_create_account_op(
            destination=destination,
            starting_balance=starting_balance,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarCreateAccountOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.new_account == destination
    assert parsed_operation.starting_balance == 1000333000


def test_stellar_parse_operation_payment_native_asset_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "XLM"
    asset_issuer = None
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarPaymentOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination
    assert parsed_operation.asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.asset.code is None
    assert parsed_operation.asset.issuer is None
    assert parsed_operation.amount == 500111000


def test_stellar_parse_operation_payment_alpha4_asset_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "USD"
    asset_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarPaymentOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination
    assert parsed_operation.asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.asset.code == asset_code
    assert parsed_operation.asset.issuer == asset_issuer
    assert parsed_operation.amount == 500111000


def test_stellar_parse_operation_payment_alpha12_asset_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "BANANA"
    asset_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarPaymentOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination
    assert parsed_operation.asset.type == stellar.ASSET_TYPE_ALPHA12
    assert parsed_operation.asset.code == asset_code
    assert parsed_operation.asset.issuer == asset_issuer
    assert parsed_operation.amount == 500111000


def test_stellar_parse_operation_path_payment_strict_receive_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    send_max = "50.0111"
    dest_amount = "100"
    send_code = "XLM"
    send_issuer = None
    dest_code = "USD"
    dest_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    path_asset1 = Asset(
        "JPY", "GD6PV7DXQJX7AGVXFQ2MTCLTCH6LR3E6IO2EO2YDZD7F7IOZZCCB5DSQ"
    )
    path_asset2 = Asset(
        "BANANA", "GC7EKO37HNSKQ3V6RZ274EO7SFOWASQRHLX3OR5FIZK6UMV6LIEDXHGZ"
    )

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_path_payment_strict_receive_op(
            destination=destination,
            send_code=send_code,
            send_issuer=send_issuer,
            send_max=send_max,
            dest_code=dest_code,
            dest_issuer=dest_issuer,
            dest_amount=dest_amount,
            path=[path_asset1, path_asset2],
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]

    assert isinstance(parsed_operation, messages.StellarPathPaymentOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination
    assert parsed_operation.send_asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.send_max == 500111000
    assert parsed_operation.destination_asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.destination_asset.code == dest_code
    assert parsed_operation.destination_asset.issuer == dest_issuer
    assert len(parsed_operation.paths) == 2
    assert parsed_operation.paths[0].type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.paths[0].code == path_asset1.code
    assert parsed_operation.paths[0].issuer == path_asset1.issuer
    assert parsed_operation.paths[1].type == stellar.ASSET_TYPE_ALPHA12
    assert parsed_operation.paths[1].code == path_asset2.code
    assert parsed_operation.paths[1].issuer == path_asset2.issuer


def test_stellar_parse_operation_path_payment_strict_receive_empty_path_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    send_max = "50.0111"
    dest_amount = "100"
    send_code = "XLM"
    send_issuer = None
    dest_code = "USD"
    dest_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_path_payment_strict_receive_op(
            destination=destination,
            send_code=send_code,
            send_issuer=send_issuer,
            send_max=send_max,
            dest_code=dest_code,
            dest_issuer=dest_issuer,
            dest_amount=dest_amount,
            path=[],
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarPathPaymentOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination
    assert parsed_operation.send_asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.send_max == 500111000
    assert parsed_operation.destination_asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.destination_asset.code == dest_code
    assert parsed_operation.destination_asset.issuer == dest_issuer
    assert len(parsed_operation.paths) == 0


def test_stellar_parse_operation_manage_sell_offer_new_offer_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_manage_sell_offer_op(
            selling_code=selling_code,
            selling_issuer=selling_issuer,
            buying_code=buying_code,
            buying_issuer=buying_issuer,
            amount=amount,
            price=price,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarManageOfferOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.selling_asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.buying_asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.buying_asset.code == buying_code
    assert parsed_operation.buying_asset.issuer == buying_issuer
    assert parsed_operation.amount == 500111000
    assert parsed_operation.price_n == 1
    assert parsed_operation.price_d == 2
    assert parsed_operation.offer_id == 0  # indicates a new offer


def test_stellar_parse_operation_manage_sell_offer_update_offer_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    offer_id = 12345
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_manage_sell_offer_op(
            selling_code=selling_code,
            selling_issuer=selling_issuer,
            buying_code=buying_code,
            buying_issuer=buying_issuer,
            amount=amount,
            price=price,
            offer_id=offer_id,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarManageOfferOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.selling_asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.buying_asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.buying_asset.code == buying_code
    assert parsed_operation.buying_asset.issuer == buying_issuer
    assert parsed_operation.amount == 500111000
    assert parsed_operation.price_n == 1
    assert parsed_operation.price_d == 2
    assert parsed_operation.offer_id == offer_id


def test_stellar_parse_operation_create_passive_sell_offer_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_create_passive_sell_offer_op(
            selling_code=selling_code,
            selling_issuer=selling_issuer,
            buying_code=buying_code,
            buying_issuer=buying_issuer,
            amount=amount,
            price=price,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarCreatePassiveOfferOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.selling_asset.type == stellar.ASSET_TYPE_NATIVE
    assert parsed_operation.buying_asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.buying_asset.code == buying_code
    assert parsed_operation.buying_asset.issuer == buying_issuer
    assert parsed_operation.amount == 500111000
    assert parsed_operation.price_n == 1
    assert parsed_operation.price_d == 2


def test_stellar_parse_operation_set_options_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    inflation_dest = "GAXN7HZQTHIPW7N2HGPAXMR42LPJ5VLYXMCCOX4D3JC4CQZGID3UYUPF"
    clear_flags = 1
    set_flags = 6
    master_weight = 255
    low_threshold = 10
    med_threshold = 20
    high_threshold = 30
    home_domain = "example.com"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_set_options_op(
            inflation_dest=inflation_dest,
            clear_flags=clear_flags,
            set_flags=set_flags,
            master_weight=master_weight,
            low_threshold=low_threshold,
            med_threshold=med_threshold,
            high_threshold=high_threshold,
            home_domain=home_domain,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarSetOptionsOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.inflation_destination_account == inflation_dest
    assert parsed_operation.clear_flags == clear_flags
    assert parsed_operation.set_flags == set_flags
    assert parsed_operation.master_weight == master_weight
    assert parsed_operation.low_threshold == low_threshold
    assert parsed_operation.medium_threshold == med_threshold
    assert parsed_operation.high_threshold == high_threshold
    assert parsed_operation.home_domain == home_domain
    assert parsed_operation.signer_type is None
    assert parsed_operation.signer_key is None
    assert parsed_operation.signer_weight is None


def test_stellar_parse_operation_set_options_ed25519_signer_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    signer = "GAXN7HZQTHIPW7N2HGPAXMR42LPJ5VLYXMCCOX4D3JC4CQZGID3UYUPF"
    weight = 10
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_ed25519_public_key_signer(
            account_id=signer, weight=weight, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarSetOptionsOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.inflation_destination_account is None
    assert parsed_operation.clear_flags is None
    assert parsed_operation.set_flags is None
    assert parsed_operation.master_weight is None
    assert parsed_operation.low_threshold is None
    assert parsed_operation.medium_threshold is None
    assert parsed_operation.high_threshold is None
    assert parsed_operation.home_domain is None
    assert parsed_operation.signer_type == 0
    assert parsed_operation.signer_key == StrKey.decode_ed25519_public_key(signer)
    assert parsed_operation.signer_weight == weight


def test_stellar_parse_operation_set_options_pre_auth_tx_signer_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    signer = bytes.fromhex(
        "2db4b22ca018119c5027a80578813ffcf582cda4aa9e31cd92b43cfa4fc5a000"
    )
    weight = 30
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_pre_auth_tx_signer(
            pre_auth_tx_hash=signer, weight=weight, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarSetOptionsOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.inflation_destination_account is None
    assert parsed_operation.clear_flags is None
    assert parsed_operation.set_flags is None
    assert parsed_operation.master_weight is None
    assert parsed_operation.low_threshold is None
    assert parsed_operation.medium_threshold is None
    assert parsed_operation.high_threshold is None
    assert parsed_operation.home_domain is None
    assert parsed_operation.signer_type == 1
    assert parsed_operation.signer_key == signer
    assert parsed_operation.signer_weight == weight


def test_stellar_parse_operation_set_options_hashx_signer_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    signer = bytes.fromhex(
        "3389e9f0f1a65f19736cacf544c2e825313e8447f569233bb8db39aa607c8000"
    )
    weight = 20
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_hashx_signer(sha256_hash=signer, weight=weight, source=operation_source)
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarSetOptionsOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.inflation_destination_account is None
    assert parsed_operation.clear_flags is None
    assert parsed_operation.set_flags is None
    assert parsed_operation.master_weight is None
    assert parsed_operation.low_threshold is None
    assert parsed_operation.medium_threshold is None
    assert parsed_operation.high_threshold is None
    assert parsed_operation.home_domain is None
    assert parsed_operation.signer_type == 2
    assert parsed_operation.signer_key == signer
    assert parsed_operation.signer_weight == weight


def test_stellar_parse_operation_change_trust_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    asset_code = "USD"
    asset_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    limit = "1000"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_change_trust_op(
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            limit=limit,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarChangeTrustOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.asset.type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.asset.code == asset_code
    assert parsed_operation.asset.issuer == asset_issuer
    assert parsed_operation.limit == 10000000000


def test_stellar_parse_operation_allow_trust_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    asset_code = "USD"
    trustor = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_allow_trust_op(
            trustor=trustor,
            asset_code=asset_code,
            authorize=TrustLineEntryFlag.AUTHORIZED_FLAG,
            source=operation_source,
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarAllowTrustOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.asset_type == stellar.ASSET_TYPE_ALPHA4
    assert parsed_operation.asset_code == asset_code
    assert parsed_operation.trusted_account == trustor
    assert parsed_operation.is_authorized == TrustLineEntryFlag.AUTHORIZED_FLAG.value


def test_stellar_parse_operation_allow_trust_unsupport_flag_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    asset_code = "USD"
    trustor = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
            v1=True,
        )
        .append_allow_trust_op(
            trustor=trustor,
            asset_code=asset_code,
            authorize=TrustLineEntryFlag.AUTHORIZED_TO_MAINTAIN_LIABILITIES_FLAG,
            source=operation_source,
        )
        .build()
    )

    with pytest.raises(ValueError, match="Unsupported trust line flag"):
        stellar.from_envelope(envelope)


def test_stellar_parse_operation_account_merge_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_account_merge_op(destination=destination, source=operation_source)
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarAccountMergeOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.destination_account == destination


def test_stellar_parse_operation_manage_data_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarManageDataOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.key == data_name
    assert parsed_operation.value == data_value


def test_stellar_parse_operation_manage_data_remove_data_entity_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    data_name = "Trezor"
    data_value = None  # remove data entity
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarManageDataOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.key == data_name
    assert parsed_operation.value is None


def test_stellar_parse_operation_bump_sequence_v1():
    network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
    tx_source = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    sequence = 123456
    bump_to = 143487250972278900
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    source_account = Account(account_id=tx_source, sequence=sequence)
    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        .append_bump_sequence_op(bump_to=bump_to, source=operation_source)
        .build()
    )

    parsed_tx, parsed_operations = stellar.from_envelope(envelope)
    assert len(parsed_operations) == 1
    parsed_operation = parsed_operations[0]
    assert isinstance(parsed_operation, messages.StellarBumpSequenceOp)
    assert parsed_operation.source_account == operation_source
    assert parsed_operation.bump_to == bump_to
