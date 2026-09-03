from typing import TYPE_CHECKING

from trezor import utils

from ..keychain import with_keychain

if TYPE_CHECKING:
    from typing import Protocol

    from trezor.messages import SignTx, TxRequest

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

    from ..authorization import CoinJoinAuthorization
    from . import approvers

    class SignerClass(Protocol):
        tx_req: TxRequest

        def __init__(  # pylint: disable=super-init-not-called
            self,
            tx: SignTx,
            keychain: Keychain,
            coin: CoinInfo,
            approver: approvers.Approver | None,
        ) -> None: ...

        async def signer(self) -> None: ...


@with_keychain
async def sign_tx(
    msg: SignTx,
    keychain: Keychain,
    coin: CoinInfo,
    authorization: CoinJoinAuthorization | None = None,
) -> TxRequest:
    from trezor import TR
    from trezor.ui.layouts import show_continue_in_app

    from ..common import BITCOIN_NAMES
    from . import approvers, bitcoin

    approver: approvers.Approver | None = None
    if authorization:
        approver = approvers.CoinJoinApprover(msg, coin, authorization)

    if utils.BITCOIN_ONLY or coin.coin_name in BITCOIN_NAMES:
        signer_class: type[SignerClass] = bitcoin.Bitcoin
    else:
        if coin.decred:
            from . import decred

            signer_class = decred.Decred
        elif coin.overwintered:
            if msg.version == 5:
                from apps.zcash.signer import Zcash

                signer_class = Zcash
            else:
                from . import zcash_v4

                signer_class = zcash_v4.ZcashV4
        else:
            from . import bitcoinlike

            signer_class = bitcoinlike.Bitcoinlike

    signer = signer_class(msg, keychain, coin, approver)
    await signer.signer()
    show_continue_in_app(TR.send__transaction_signed)
    return signer.tx_req
