from micropython import const

from trezor import wire
from trezor.messages import AuthorizeCoinJoin

from apps.common import authorization

from .common import BIP32_WALLET_DEPTH

if False:
    from trezor.messages import (
        GetOwnershipProof,
        SignTx,
        TxInput,
    )
    from trezor.protobuf import MessageType

    from apps.common.coininfo import CoinInfo

_ROUND_ID_LEN = const(32)
FEE_PER_ANONYMITY_DECIMALS = const(9)


class CoinJoinAuthorization:
    def __init__(self, params: AuthorizeCoinJoin) -> None:
        self.params = params

    def check_get_ownership_proof(self, msg: GetOwnershipProof) -> bool:
        # Check whether the current params matches the parameters of the request.
        return (
            len(msg.address_n) >= BIP32_WALLET_DEPTH
            and msg.address_n[:-BIP32_WALLET_DEPTH] == self.params.address_n
            and msg.coin_name == self.params.coin_name
            and msg.script_type == self.params.script_type
            and len(msg.commitment_data) >= _ROUND_ID_LEN
            and msg.commitment_data[:-_ROUND_ID_LEN] == self.params.coordinator.encode()
        )

    def check_sign_tx_input(self, txi: TxInput, coin: CoinInfo) -> bool:
        # Check whether the current input matches the parameters of the request.
        return (
            len(txi.address_n) >= BIP32_WALLET_DEPTH
            and txi.address_n[:-BIP32_WALLET_DEPTH] == self.params.address_n
            and coin.coin_name == self.params.coin_name
            and txi.script_type == self.params.script_type
        )

    def approve_sign_tx(self, msg: SignTx, fee: int) -> bool:
        if self.params.max_total_fee < fee or msg.coin_name != self.params.coin_name:
            return False

        self.params.max_total_fee -= fee
        authorization.set(self.params)
        return True


def from_cached_message(auth_msg: MessageType) -> CoinJoinAuthorization:
    if not AuthorizeCoinJoin.is_type_of(auth_msg):
        raise wire.ProcessError("Appropriate params was not found")

    return CoinJoinAuthorization(auth_msg)
