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

from base64 import b64decode, b64encode

import pytest
from stellar_sdk import Keypair, TransactionEnvelope

from trezorlib import protobuf
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from . import stellar_ext
from .common import COMMON_FIXTURES_DIR, parametrize_using_common_fixtures
from .generated import messages as stellar_messages


def parameters_to_proto(parameters):
    tx_data = parameters["tx"]
    ops_data = parameters["operations"]
    ext_data = parameters.get("ext")

    tx_data["address_n"] = parse_path(parameters["address_n"])
    tx_data["network_passphrase"] = parameters["network_passphrase"]
    tx_data["num_operations"] = len(ops_data)

    if ext_data:
        soroban_data_hex = ext_data.get("soroban_data")
        soroban_data = bytes.fromhex(soroban_data_hex) if soroban_data_hex else None
        ext = stellar_messages.TxExt(v=ext_data["v"], soroban_data=soroban_data)
    else:
        ext = stellar_messages.TxExt(v=0)

    def make_op(operation_data):
        type_name = operation_data["_message_type"]
        assert type_name.startswith("Stellar") and type_name.endswith("Op")
        cls = getattr(stellar_messages, type_name.removeprefix("Stellar"))
        return protobuf.dict_to_proto(cls, operation_data)

    tx = protobuf.dict_to_proto(stellar_messages.SignTx, tx_data)
    operations = [make_op(op) for op in ops_data]
    return tx, operations, ext


def _skip_payment_request(parameters):
    if parameters.get("payment_request"):
        # The coin purchase memo of the payment request carries a MAC of another
        # coin, which Core can only verify with the coin type of the app.
        pytest.skip("payment requests need a MAC of another coin type")


@parametrize_using_common_fixtures("sign_tx.json")
def test_sign_tx(session: Session, instance_id: int, parameters, result):
    _skip_payment_request(parameters)
    tx, operations, ext = parameters_to_proto(parameters)
    envelope = TransactionEnvelope.from_xdr(
        parameters["xdr"], parameters["network_passphrase"]
    )

    if "signature" in result:
        pubkey = bytes.fromhex(result["public_key"])
        keypair = Keypair.from_raw_ed25519_public_key(pubkey)
        keypair.verify(envelope.hash(), b64decode(result["signature"]))

        response = stellar_ext.sign_tx(
            session,
            instance_id,
            tx,
            operations,
            ext,
            tx.address_n,
            tx.network_passphrase,
        )
        assert response.public_key.hex() == result["public_key"]
        assert b64encode(response.signature).decode() == result["signature"]
    elif "error_message" in result:
        with pytest.raises(TrezorFailure, match=result["error_message"]):
            stellar_ext.sign_tx(
                session,
                instance_id,
                tx,
                operations,
                ext,
                tx.address_n,
                tx.network_passphrase,
            )
    else:
        assert False, "Invalid expected result"


def test_sign_tx_asset_hint_mismatch(session: Session, instance_id: int):
    """A hint that does not derive to the invoked contract is ignored.

    trezorlib never produces such a hint (it only attaches self-derived
    matches), so forge one directly in the protobuf of a valid fixture.
    """
    import json

    fixtures = json.loads((COMMON_FIXTURES_DIR / "sign_tx.json").read_text())
    parameters = next(
        t
        for t in fixtures["tests"]
        if t["name"] == "StellarInvokeHostFunction-sac-transfer"
    )["parameters"]
    tx, operations, ext = parameters_to_proto(parameters)

    hint = operations[0].function.invoke_contract.asset_hint
    assert hint is not None
    hint.code = "USDX"

    stellar_ext.sign_tx(
        session,
        instance_id,
        tx,
        operations,
        ext,
        tx.address_n,
        tx.network_passphrase,
    )
