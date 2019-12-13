from . import messages
from .tools import expect


@expect(messages.ElementsRangeProofNonce)
def get_rangeproof_nonce(client, ecdh_pubkey, script_pubkey):
    return client.call(
        messages.ElementsGetRangeProofNonce(
            ecdh_pubkey=ecdh_pubkey, script_pubkey=script_pubkey
        )
    )
