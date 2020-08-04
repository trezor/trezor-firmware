import utime
from micropython import const

from trezor.messages import MessageType
from trezor.messages.TxInputType import TxInputType

from .common import BIP32_WALLET_DEPTH

if False:
    from typing import Iterable
    from trezor.messages.AuthorizeCoinJoin import AuthorizeCoinJoin
    from trezor.messages.GetOwnershipProof import GetOwnershipProof
    from trezor.messages.SignTx import SignTx
    from apps.common import coininfo
    from apps.common.seed import Keychain

_ROUND_ID_LEN = const(8)
FEE_PER_ANONYMITY_DECIMALS = const(9)
_ROUND_ID_LIFETIME_MS = const(
    10 * 60 * 1000
)  # 10 minutes before a proof of ownership can be generated for another round ID


class CoinJoinAuthorization:
    def __init__(
        self, msg: AuthorizeCoinJoin, keychain: Keychain, coin: coininfo.CoinInfo
    ):
        self.coordinator = msg.coordinator
        self.round_id = bytes()
        self.round_id_expiry = 0
        self.remaining_fee = msg.max_total_fee
        self.fee_per_anonymity = msg.fee_per_anonymity or 0
        self.address_n = msg.address_n
        self.keychain = keychain
        self.coin = coin
        self.script_type = msg.script_type

    def __del__(self) -> None:
        self.keychain.__del__()

    def expected_wire_types(self) -> Iterable[int]:
        return (MessageType.SignTx, MessageType.GetOwnershipProof)

    def check_get_ownership_proof(self, msg: GetOwnershipProof) -> bool:
        # Check whether the current authorization matches the parameters of the request.
        if (
            msg.address_n[:-BIP32_WALLET_DEPTH] != self.address_n
            or msg.coin_name != self.coin.coin_name
            or msg.script_type != self.script_type
            or len(msg.commitment_data) < _ROUND_ID_LEN
            or msg.commitment_data[:-_ROUND_ID_LEN] != self.coordinator.encode()
        ):
            return False

        # Allow changing to a different round ID only after _ROUND_ID_LIFETIME_MS.
        round_id = msg.commitment_data[-_ROUND_ID_LEN:]
        if round_id == self.round_id:
            return True

        if self.round_id_expiry <= utime.ticks_ms():
            self.round_id = round_id
            self.round_id_expiry = utime.ticks_ms() + _ROUND_ID_LIFETIME_MS
            return True

        return False

    def check_sign_tx_input(self, txi: TxInputType, coin: coininfo.CoinInfo) -> bool:
        # Check whether the current input matches the parameters of the request.
        return (
            txi.address_n[:-BIP32_WALLET_DEPTH] == self.address_n
            and coin.coin_name == self.coin.coin_name
            and txi.script_type == self.script_type
        )

    def approve_sign_tx(self, msg: SignTx, fee: int) -> bool:
        if self.remaining_fee < fee or msg.coin_name != self.coin.coin_name:
            return False

        self.remaining_fee -= fee
        return True
