from typing import Type

from trezor import log, wire
from trezor.enums import CardanoTxSigningMode
from trezor.messages import CardanoSignTxFinished, CardanoSignTxInit

from .. import seed
from .signer import Signer


@seed.with_keychain
async def sign_tx(
    ctx: wire.Context, msg: messages.CardanoSignTxInit, keychain: seed.Keychain
) -> messages.CardanoSignTxFinished:
    signer_type: Type[Signer]
    if msg.signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
        from .ordinary_signer import OrdinarySigner

        signer_type = OrdinarySigner
    elif msg.signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        from .pool_owner_signer import PoolOwnerSigner

        signer_type = PoolOwnerSigner
    elif msg.signing_mode == CardanoTxSigningMode.MULTISIG_TRANSACTION:
        from .multisig_signer import MultisigSigner

        signer_type = MultisigSigner
    elif msg.signing_mode == CardanoTxSigningMode.PLUTUS_TRANSACTION:
        from .plutus_signer import PlutusSigner

        signer_type = PlutusSigner
    else:
        raise RuntimeError  # should be unreachable

    signer = signer_type(ctx, msg, keychain)

    try:
        await signer.sign()
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Signing failed")

    return CardanoSignTxFinished()
