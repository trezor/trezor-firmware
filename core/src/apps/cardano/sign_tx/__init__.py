from typing import TYPE_CHECKING

from .. import seed

if TYPE_CHECKING:
    from typing import Type

    from trezor.messages import CardanoSignTxFinished, CardanoSignTxInit

    from apps.common.keychain import Keychain as Slip21Keychain


@seed.with_keychain
async def sign_tx(
    msg: CardanoSignTxInit, keychain: seed.Keychain, slip21_keychain: Slip21Keychain
) -> CardanoSignTxFinished:
    from trezor import TR, log, wire
    from trezor.enums import CardanoTxSigningMode
    from trezor.messages import CardanoSignTxFinished
    from trezor.ui.layouts import show_continue_in_app

    from .signer import Signer

    signing_mode = msg.signing_mode  # local_cache_attribute

    signer_type: Type[Signer]
    if signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
        from .ordinary_signer import OrdinarySigner

        signer_type = OrdinarySigner
    elif signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        from .pool_owner_signer import PoolOwnerSigner

        signer_type = PoolOwnerSigner
    elif signing_mode == CardanoTxSigningMode.MULTISIG_TRANSACTION:
        from .multisig_signer import MultisigSigner

        signer_type = MultisigSigner
    elif signing_mode == CardanoTxSigningMode.PLUTUS_TRANSACTION:
        from .plutus_signer import PlutusSigner

        signer_type = PlutusSigner
    else:
        raise RuntimeError  # should be unreachable

    signer = signer_type(msg, keychain, slip21_keychain)

    try:
        await signer.sign()
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Signing failed")

    show_continue_in_app(TR.send__transaction_signed)
    return CardanoSignTxFinished()
