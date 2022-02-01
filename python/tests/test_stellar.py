# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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
from stellar_sdk import (
    Account,
    Asset,
    Network,
    TransactionBuilder,
    TrustLineEntryFlag,
    MuxedAccount,
)
from stellar_sdk.strkey import StrKey

from trezorlib import messages, stellar

TX_SOURCE = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
SEQUENCE = 123456
TIMEBOUNDS_START = 461535181
TIMEBOUNDS_END = 1575234180
BASE_FEE = 200


def make_default_tx(default_op: bool = False, **kwargs) -> TransactionBuilder:
    source_account = Account(account_id=TX_SOURCE, sequence=SEQUENCE)
    default_params = {
        "source_account": source_account,
        "network_passphrase": Network.TESTNET_NETWORK_PASSPHRASE,
        "base_fee": BASE_FEE,
    }
    default_params.update(kwargs)
    builder = TransactionBuilder(**default_params)
    builder.add_time_bounds(TIMEBOUNDS_START, TIMEBOUNDS_END)

    if default_op:
        builder.append_manage_data_op(data_name="Trezor", data_value=b"Hello, Stellar")

    return builder


def test_simple():
    envelope = make_default_tx(default_op=True).build()

    tx, operations = stellar.from_envelope(envelope)
    assert tx.source_account == TX_SOURCE
    assert tx.fee == envelope.transaction.fee
    assert tx.sequence_number == SEQUENCE + 1
    assert tx.timebounds_start is TIMEBOUNDS_START
    assert tx.timebounds_end is TIMEBOUNDS_END
    assert tx.memo_type == messages.StellarMemoType.NONE
    assert tx.memo_text is None
    assert tx.memo_id is None
    assert tx.memo_hash is None
    assert len(operations) == 1


def test_memo_text():
    memo_text = "Have a nice day!"
    envelope = (
        make_default_tx(default_op=True).add_text_memo(memo_text.encode()).build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert tx.memo_type == messages.StellarMemoType.TEXT
    assert tx.memo_text == memo_text
    assert tx.memo_id is None
    assert tx.memo_hash is None


def test_memo_id():
    memo_id = 123456789
    envelope = make_default_tx(default_op=True).add_id_memo(memo_id).build()

    tx, operations = stellar.from_envelope(envelope)
    assert tx.memo_type == messages.StellarMemoType.ID
    assert tx.memo_text is None
    assert tx.memo_id == memo_id
    assert tx.memo_hash is None


def test_memo_hash():
    memo_hash = "b77cd735095e1b58da2d7415c1f51f423a722b34d7d5002d8896608a9130a74b"
    envelope = (
        make_default_tx(v1=False, default_op=True).add_hash_memo(memo_hash).build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert tx.memo_type == messages.StellarMemoType.HASH
    assert tx.memo_text is None
    assert tx.memo_id is None
    assert tx.memo_hash.hex() == memo_hash


def test_memo_return_hash():
    memo_return = "b77cd735095e1b58da2d7415c1f51f423a722b34d7d5002d8896608a9130a74b"
    envelope = (
        make_default_tx(v1=False, default_op=True)
        .add_return_hash_memo(memo_return)
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert tx.memo_type == messages.StellarMemoType.RETURN
    assert tx.memo_text is None
    assert tx.memo_id is None
    assert tx.memo_hash.hex() == memo_return


def test_time_bounds_missing():
    tx = make_default_tx(default_op=True)
    tx.time_bounds = None
    envelope = tx.build()

    with pytest.raises(ValueError):
        stellar.from_envelope(envelope)


def test_multiple_operations():
    tx = make_default_tx()
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    operation1_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "XLM"
    asset_issuer = None
    operation2_source = "GBHWKBPP3O4H2BUUKSFXE4PK5WHLQYVZIZUNUJ4AU5VUZZEVBDMXISAS"

    envelope = (
        tx
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

    tx, operations = stellar.from_envelope(envelope)
    assert tx.source_account == TX_SOURCE
    assert tx.fee == envelope.transaction.fee
    assert tx.sequence_number == SEQUENCE + 1
    assert tx.timebounds_start is TIMEBOUNDS_START
    assert tx.timebounds_end is TIMEBOUNDS_END
    assert tx.memo_type == messages.StellarMemoType.NONE
    assert tx.memo_text is None
    assert tx.memo_id is None
    assert tx.memo_hash is None
    assert len(operations) == 2

    assert isinstance(operations[0], messages.StellarManageDataOp)
    assert operations[0].source_account == operation1_source
    assert operations[0].key == data_name
    assert operations[0].value == data_value

    assert isinstance(operations[1], messages.StellarPaymentOp)
    assert operations[1].source_account == operation2_source
    assert operations[1].destination_account == destination
    assert operations[1].asset.type == messages.StellarAssetType.NATIVE
    assert operations[1].asset.code is None
    assert operations[1].asset.issuer is None
    assert operations[1].amount == 500111000


def test_create_account():
    tx = make_default_tx()
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    starting_balance = "100.0333"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_create_account_op(
            destination=destination,
            starting_balance=starting_balance,
            source=operation_source,
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarCreateAccountOp)
    assert operations[0].source_account == operation_source
    assert operations[0].new_account == destination
    assert operations[0].starting_balance == 1000333000


def test_payment_native_asset():
    tx = make_default_tx()
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "XLM"
    asset_issuer = None
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation_source,
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarPaymentOp)
    assert operations[0].source_account == operation_source
    assert operations[0].destination_account == destination
    assert operations[0].asset.type == messages.StellarAssetType.NATIVE
    assert operations[0].asset.code is None
    assert operations[0].asset.issuer is None
    assert operations[0].amount == 500111000


def test_payment_alpha4_asset():
    tx = make_default_tx()
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "USD"
    asset_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation_source,
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarPaymentOp)
    assert operations[0].source_account == operation_source
    assert operations[0].destination_account == destination
    assert operations[0].asset.type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].asset.code == asset_code
    assert operations[0].asset.issuer == asset_issuer
    assert operations[0].amount == 500111000


def test_payment_alpha12_asset():
    tx = make_default_tx()
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "BANANA"
    asset_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation_source,
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarPaymentOp)
    assert operations[0].source_account == operation_source
    assert operations[0].destination_account == destination
    assert operations[0].asset.type == messages.StellarAssetType.ALPHANUM12
    assert operations[0].asset.code == asset_code
    assert operations[0].asset.issuer == asset_issuer
    assert operations[0].amount == 500111000


def test_path_payment_strict_receive():
    tx = make_default_tx()
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

    envelope = (
        tx
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

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1

    assert isinstance(operations[0], messages.StellarPathPaymentStrictReceiveOp)
    assert operations[0].source_account == operation_source
    assert operations[0].destination_account == destination
    assert operations[0].send_asset.type == messages.StellarAssetType.NATIVE
    assert operations[0].send_max == 500111000
    assert operations[0].destination_amount == 1000000000
    assert operations[0].destination_asset.type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].destination_asset.code == dest_code
    assert operations[0].destination_asset.issuer == dest_issuer
    assert len(operations[0].paths) == 2
    assert operations[0].paths[0].type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].paths[0].code == path_asset1.code
    assert operations[0].paths[0].issuer == path_asset1.issuer
    assert operations[0].paths[1].type == messages.StellarAssetType.ALPHANUM12
    assert operations[0].paths[1].code == path_asset2.code
    assert operations[0].paths[1].issuer == path_asset2.issuer


def test_manage_sell_offer_new_offer():
    tx = make_default_tx()
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
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

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarManageSellOfferOp)
    assert operations[0].source_account == operation_source
    assert operations[0].selling_asset.type == messages.StellarAssetType.NATIVE
    assert operations[0].buying_asset.type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].buying_asset.code == buying_code
    assert operations[0].buying_asset.issuer == buying_issuer
    assert operations[0].amount == 500111000
    assert operations[0].price_n == 1
    assert operations[0].price_d == 2
    assert operations[0].offer_id == 0  # indicates a new offer


def test_manage_sell_offer_update_offer():
    tx = make_default_tx()
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    offer_id = 12345
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
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

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarManageSellOfferOp)
    assert operations[0].source_account == operation_source
    assert operations[0].selling_asset.type == messages.StellarAssetType.NATIVE
    assert operations[0].buying_asset.type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].buying_asset.code == buying_code
    assert operations[0].buying_asset.issuer == buying_issuer
    assert operations[0].amount == 500111000
    assert operations[0].price_n == 1
    assert operations[0].price_d == 2
    assert operations[0].offer_id == offer_id


def test_create_passive_sell_offer():
    tx = make_default_tx()
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
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

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarCreatePassiveSellOfferOp)
    assert operations[0].source_account == operation_source
    assert operations[0].selling_asset.type == messages.StellarAssetType.NATIVE
    assert operations[0].buying_asset.type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].buying_asset.code == buying_code
    assert operations[0].buying_asset.issuer == buying_issuer
    assert operations[0].amount == 500111000
    assert operations[0].price_n == 1
    assert operations[0].price_d == 2


def test_set_options():
    tx = make_default_tx()
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"
    inflation_dest = "GAXN7HZQTHIPW7N2HGPAXMR42LPJ5VLYXMCCOX4D3JC4CQZGID3UYUPF"
    clear_flags = 1
    set_flags = 6
    master_weight = 255
    low_threshold = 10
    med_threshold = 20
    high_threshold = 30
    home_domain = "example.com"

    envelope = (
        tx
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

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarSetOptionsOp)
    assert operations[0].source_account == operation_source
    assert operations[0].inflation_destination_account == inflation_dest
    assert operations[0].clear_flags == clear_flags
    assert operations[0].set_flags == set_flags
    assert operations[0].master_weight == master_weight
    assert operations[0].low_threshold == low_threshold
    assert operations[0].medium_threshold == med_threshold
    assert operations[0].high_threshold == high_threshold
    assert operations[0].home_domain == home_domain
    assert operations[0].signer_type is None
    assert operations[0].signer_key is None
    assert operations[0].signer_weight is None


def test_set_options_ed25519_signer():
    tx = make_default_tx()
    signer = "GAXN7HZQTHIPW7N2HGPAXMR42LPJ5VLYXMCCOX4D3JC4CQZGID3UYUPF"
    weight = 10
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_ed25519_public_key_signer(
            account_id=signer, weight=weight, source=operation_source
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarSetOptionsOp)
    assert operations[0].source_account == operation_source
    assert operations[0].inflation_destination_account is None
    assert operations[0].clear_flags is None
    assert operations[0].set_flags is None
    assert operations[0].master_weight is None
    assert operations[0].low_threshold is None
    assert operations[0].medium_threshold is None
    assert operations[0].high_threshold is None
    assert operations[0].home_domain is None
    assert operations[0].signer_type == messages.StellarSignerType.ACCOUNT
    assert operations[0].signer_key == StrKey.decode_ed25519_public_key(signer)
    assert operations[0].signer_weight == weight


def test_set_options_pre_auth_tx_signer():
    tx = make_default_tx()
    signer = bytes.fromhex(
        "2db4b22ca018119c5027a80578813ffcf582cda4aa9e31cd92b43cfa4fc5a000"
    )
    weight = 30
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_pre_auth_tx_signer(
            pre_auth_tx_hash=signer, weight=weight, source=operation_source
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarSetOptionsOp)
    assert operations[0].signer_type == messages.StellarSignerType.PRE_AUTH
    assert operations[0].signer_key == signer
    assert operations[0].signer_weight == weight


def test_set_options_hashx_signer():
    tx = make_default_tx()
    signer = bytes.fromhex(
        "3389e9f0f1a65f19736cacf544c2e825313e8447f569233bb8db39aa607c8000"
    )
    weight = 20
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_hashx_signer(sha256_hash=signer, weight=weight, source=operation_source)
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarSetOptionsOp)
    assert operations[0].signer_type == messages.StellarSignerType.HASH
    assert operations[0].signer_key == signer
    assert operations[0].signer_weight == weight


def test_change_trust():
    tx = make_default_tx()
    asset_code = "USD"
    asset_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    limit = "1000"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_change_trust_op(
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            limit=limit,
            source=operation_source,
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarChangeTrustOp)
    assert operations[0].source_account == operation_source
    assert operations[0].asset.type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].asset.code == asset_code
    assert operations[0].asset.issuer == asset_issuer
    assert operations[0].limit == 10000000000


def test_allow_trust():
    tx = make_default_tx()
    asset_code = "USD"
    trustor = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_allow_trust_op(
            trustor=trustor,
            asset_code=asset_code,
            authorize=TrustLineEntryFlag.AUTHORIZED_FLAG,
            source=operation_source,
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarAllowTrustOp)
    assert operations[0].source_account == operation_source
    assert operations[0].asset_type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].asset_code == asset_code
    assert operations[0].trusted_account == trustor
    assert operations[0].is_authorized is True


def test_account_merge():
    tx = make_default_tx()
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_account_merge_op(destination=destination, source=operation_source)
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarAccountMergeOp)
    assert operations[0].source_account == operation_source
    assert operations[0].destination_account == destination


def test_manage_data():
    tx = make_default_tx()
    data_name = "Trezor"
    data_value = b"Hello, Stellar"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarManageDataOp)
    assert operations[0].source_account == operation_source
    assert operations[0].key == data_name
    assert operations[0].value == data_value


def test_manage_data_remove_data_entity():
    tx = make_default_tx()
    data_name = "Trezor"
    data_value = None  # remove data entity
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_manage_data_op(
            data_name=data_name, data_value=data_value, source=operation_source
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarManageDataOp)
    assert operations[0].source_account == operation_source
    assert operations[0].key == data_name
    assert operations[0].value is None


def test_bump_sequence():
    tx = make_default_tx()
    bump_to = 143487250972278900
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        tx
        .append_bump_sequence_op(bump_to=bump_to, source=operation_source)
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarBumpSequenceOp)
    assert operations[0].source_account == operation_source
    assert operations[0].bump_to == bump_to


def test_manage_buy_offer_new_offer():
    tx = make_default_tx()
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = tx.append_manage_buy_offer_op(
        selling_code=selling_code,
        selling_issuer=selling_issuer,
        buying_code=buying_code,
        buying_issuer=buying_issuer,
        amount=amount,
        price=price,
        source=operation_source,
    ).build()

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarManageBuyOfferOp)
    assert operations[0].source_account == operation_source
    assert operations[0].selling_asset.type == messages.StellarAssetType.NATIVE
    assert operations[0].buying_asset.type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].buying_asset.code == buying_code
    assert operations[0].buying_asset.issuer == buying_issuer
    assert operations[0].amount == 500111000
    assert operations[0].price_n == 1
    assert operations[0].price_d == 2
    assert operations[0].offer_id == 0  # indicates a new offer


def test_manage_buy_offer_update_offer():
    tx = make_default_tx()
    price = "0.5"
    amount = "50.0111"
    selling_code = "XLM"
    selling_issuer = None
    buying_code = "USD"
    buying_issuer = "GCSJ7MFIIGIRMAS4R3VT5FIFIAOXNMGDI5HPYTWS5X7HH74FSJ6STSGF"
    offer_id = 12345
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = tx.append_manage_buy_offer_op(
        selling_code=selling_code,
        selling_issuer=selling_issuer,
        buying_code=buying_code,
        buying_issuer=buying_issuer,
        amount=amount,
        price=price,
        offer_id=offer_id,
        source=operation_source,
    ).build()

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1
    assert isinstance(operations[0], messages.StellarManageBuyOfferOp)
    assert operations[0].source_account == operation_source
    assert operations[0].selling_asset.type == messages.StellarAssetType.NATIVE
    assert operations[0].buying_asset.type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].buying_asset.code == buying_code
    assert operations[0].buying_asset.issuer == buying_issuer
    assert operations[0].amount == 500111000
    assert operations[0].price_n == 1
    assert operations[0].price_d == 2
    assert operations[0].offer_id == offer_id


def test_path_payment_strict_send():
    tx = make_default_tx()
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    send_amount = "50.0112"
    dest_min = "120"
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

    envelope = (
        tx
        .append_path_payment_strict_send_op(
            destination=destination,
            send_code=send_code,
            send_issuer=send_issuer,
            send_amount=send_amount,
            dest_code=dest_code,
            dest_issuer=dest_issuer,
            dest_min=dest_min,
            path=[path_asset1, path_asset2],
            source=operation_source,
        )
        .build()
    )

    tx, operations = stellar.from_envelope(envelope)
    assert len(operations) == 1

    assert isinstance(operations[0], messages.StellarPathPaymentStrictSendOp)
    assert operations[0].source_account == operation_source
    assert operations[0].destination_account == destination
    assert operations[0].send_asset.type == messages.StellarAssetType.NATIVE
    assert operations[0].send_amount == 500112000
    assert operations[0].destination_min == 1200000000
    assert operations[0].destination_asset.type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].destination_asset.code == dest_code
    assert operations[0].destination_asset.issuer == dest_issuer
    assert len(operations[0].paths) == 2
    assert operations[0].paths[0].type == messages.StellarAssetType.ALPHANUM4
    assert operations[0].paths[0].code == path_asset1.code
    assert operations[0].paths[0].issuer == path_asset1.issuer
    assert operations[0].paths[1].type == messages.StellarAssetType.ALPHANUM12
    assert operations[0].paths[1].code == path_asset2.code
    assert operations[0].paths[1].issuer == path_asset2.issuer


def test_payment_muxed_account_not_support_raise():
    tx = make_default_tx()
    destination = MuxedAccount(
        "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6", 1
    )
    amount = "50.0111"
    asset_code = "XLM"
    asset_issuer = None
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = tx.append_payment_op(
        destination=destination,
        amount=amount,
        asset_code=asset_code,
        asset_issuer=asset_issuer,
        source=operation_source,
    ).build()

    with pytest.raises(ValueError, match="MuxedAccount is not supported"):
        stellar.from_envelope(envelope)


def test_path_payment_strict_send_muxed_account_not_support_raise():
    tx = make_default_tx()
    destination = MuxedAccount(
        "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6", 1
    )
    send_amount = "50.0112"
    dest_min = "120"
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

    envelope = tx.append_path_payment_strict_send_op(
        destination=destination,
        send_code=send_code,
        send_issuer=send_issuer,
        send_amount=send_amount,
        dest_code=dest_code,
        dest_issuer=dest_issuer,
        dest_min=dest_min,
        path=[path_asset1, path_asset2],
        source=operation_source,
    ).build()

    with pytest.raises(ValueError, match="MuxedAccount is not supported"):
        stellar.from_envelope(envelope)


def test_path_payment_strict_receive_muxed_account_not_support_raise():
    tx = make_default_tx()
    destination = MuxedAccount(
        "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6", 1
    )
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

    envelope = tx.append_path_payment_strict_receive_op(
        destination=destination,
        send_code=send_code,
        send_issuer=send_issuer,
        send_max=send_max,
        dest_code=dest_code,
        dest_issuer=dest_issuer,
        dest_amount=dest_amount,
        path=[path_asset1, path_asset2],
        source=operation_source,
    ).build()

    with pytest.raises(ValueError, match="MuxedAccount is not supported"):
        stellar.from_envelope(envelope)


def test_account_merge_muxed_account_not_support_raise():
    tx = make_default_tx()
    destination = MuxedAccount(
        "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6", 1
    )
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = tx.append_account_merge_op(
        destination=destination, source=operation_source
    ).build()

    with pytest.raises(ValueError, match="MuxedAccount is not supported"):
        stellar.from_envelope(envelope)


def test_op_source_muxed_account_not_support_raise():
    tx = make_default_tx()
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "XLM"
    asset_issuer = None
    operation_source = MuxedAccount(
        "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V", 2
    )

    envelope = tx.append_payment_op(
        destination=destination,
        amount=amount,
        asset_code=asset_code,
        asset_issuer=asset_issuer,
        source=operation_source,
    ).build()

    with pytest.raises(ValueError, match="MuxedAccount is not supported"):
        stellar.from_envelope(envelope)


def test_tx_source_muxed_account_not_support_raise():
    source_account = Account(
        account_id=MuxedAccount(TX_SOURCE, 123456), sequence=SEQUENCE
    )
    destination = "GDNSSYSCSSJ76FER5WEEXME5G4MTCUBKDRQSKOYP36KUKVDB2VCMERS6"
    amount = "50.0111"
    asset_code = "XLM"
    asset_issuer = None
    operation_source = "GAEB4MRKRCONK4J7MVQXAHTNDPAECUCCCNE7YC5CKM34U3OJ673A4D6V"

    envelope = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
            base_fee=BASE_FEE,
        )
        .add_time_bounds(TIMEBOUNDS_START, TIMEBOUNDS_END)
        .append_payment_op(
            destination=destination,
            amount=amount,
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            source=operation_source,
        )
        .build()
    )

    with pytest.raises(ValueError, match="MuxedAccount is not supported"):
        stellar.from_envelope(envelope)
