from base64 import b64decode, b64encode

import pytest
from stellar_sdk import Keypair
from stellar_sdk import auth as stellar_auth
from stellar_sdk import xdr as stellar_xdr

from trezorlib import protobuf
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from . import stellar_ext
from .common import parametrize_using_common_fixtures
from .generated import messages as stellar_messages


@parametrize_using_common_fixtures("sign_soroban_authorization.json")
def test_sign_soroban_authorization(
    session: Session, instance_id: int, parameters, result
):
    authorization = protobuf.dict_to_proto(
        stellar_messages.SorobanAuthorizationWithAddress,
        parameters["authorization"],
    )
    entry = stellar_xdr.SorobanAuthorizationEntry.from_xdr(parameters["xdr"])

    if "signature" in result:
        assert entry.credentials.address_v2 is not None
        payload = stellar_auth.authorization_payload_hash(
            stellar_auth.build_authorization_preimage(
                entry,
                valid_until_ledger_sequence=entry.credentials.address_v2.signature_expiration_ledger.uint32,
                network_passphrase=parameters["network_passphrase"],
            )
        )
        pubkey = bytes.fromhex(result["public_key"])
        keypair = Keypair.from_raw_ed25519_public_key(pubkey)
        keypair.verify(payload, b64decode(result["signature"]))

        response = stellar_ext.sign_soroban_authorization(
            session,
            instance_id,
            parse_path(parameters["address_n"]),
            parameters["network_passphrase"],
            authorization,
        )
        assert response.public_key.hex() == result["public_key"]
        assert b64encode(response.signature).decode() == result["signature"]
    elif "error_message" in result:
        with pytest.raises(TrezorFailure, match=result["error_message"]):
            stellar_ext.sign_soroban_authorization(
                session,
                instance_id,
                parse_path(parameters["address_n"]),
                parameters["network_passphrase"],
                authorization,
            )
    else:
        assert False, "Invalid expected result"
