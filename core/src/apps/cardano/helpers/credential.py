from typing import TYPE_CHECKING

from trezor.enums import CardanoAddressType

from ...common.paths import address_n_to_str
from . import bech32
from .paths import CHAIN_STAKING_KEY, SCHEMA_PAYMENT, SCHEMA_STAKING
from .utils import to_account_path

if TYPE_CHECKING:
    from trezor import messages
    from trezor.ui.layouts import PropertyType

CREDENTIAL_TYPE_PAYMENT: str = "payment"
CREDENTIAL_TYPE_STAKE: str = "stake"


class Credential:
    """
    Serves mainly as a wrapper object for credentials (so that they don't have to be
    passed into functions separately) which also determines all properties that should be shown
    as warnings.
    Also contains functions which simplify displaying the credential.
    """

    type_name: str
    address_type: CardanoAddressType
    path: list[int]
    key_hash: bytes | None
    script_hash: bytes | None
    pointer: messages.CardanoBlockchainPointerType | None

    is_reward: bool = False
    is_no_staking: bool = False
    is_mismatch: bool = False
    is_unusual_path: bool = False
    is_other_warning: bool = False

    def __init__(
        self,
        type_name: str,
        address_type: CardanoAddressType,
        path: list[int],
        key_hash: bytes | None,
        script_hash: bytes | None,
        pointer: messages.CardanoBlockchainPointerType | None,
    ):
        self.type_name = type_name
        self.address_type = address_type
        self.path = path
        self.key_hash = key_hash
        self.script_hash = script_hash
        self.pointer = pointer

    @classmethod
    def payment_credential(
        cls, address_params: messages.CardanoAddressParametersType
    ) -> "Credential":
        address_type = address_params.address_type
        credential = cls(
            type_name=CREDENTIAL_TYPE_PAYMENT,
            address_type=address_type,
            path=address_params.address_n,
            key_hash=None,
            script_hash=address_params.script_payment_hash,
            pointer=None,
        )

        if address_type in (
            CardanoAddressType.BASE,
            CardanoAddressType.BASE_KEY_SCRIPT,
            CardanoAddressType.POINTER,
            CardanoAddressType.ENTERPRISE,
            CardanoAddressType.BYRON,
        ):
            if not SCHEMA_PAYMENT.match(address_params.address_n):
                credential.is_unusual_path = True

        elif address_type in (
            CardanoAddressType.BASE_SCRIPT_KEY,
            CardanoAddressType.BASE_SCRIPT_SCRIPT,
            CardanoAddressType.POINTER_SCRIPT,
            CardanoAddressType.ENTERPRISE_SCRIPT,
        ):
            credential.is_other_warning = True

        elif address_type in (
            CardanoAddressType.REWARD,
            CardanoAddressType.REWARD_SCRIPT,
        ):
            credential.is_reward = True

        else:
            raise RuntimeError  # we didn't cover all address types

        return credential

    @classmethod
    def stake_credential(
        cls, address_params: messages.CardanoAddressParametersType
    ) -> "Credential":
        address_type = address_params.address_type
        credential = cls(
            type_name=CREDENTIAL_TYPE_STAKE,
            address_type=address_type,
            path=address_params.address_n_staking,
            key_hash=address_params.staking_key_hash,
            script_hash=address_params.script_staking_hash,
            pointer=address_params.certificate_pointer,
        )

        if address_type == CardanoAddressType.BASE:
            if address_params.staking_key_hash:
                credential.is_other_warning = True
            else:
                if not SCHEMA_STAKING.match(address_params.address_n_staking):
                    credential.is_unusual_path = True
                if not _do_base_address_credentials_match(
                    address_params.address_n,
                    address_params.address_n_staking,
                ):
                    credential.is_mismatch = True

        elif address_type == CardanoAddressType.BASE_SCRIPT_KEY:
            if address_params.address_n_staking and not SCHEMA_STAKING.match(
                address_params.address_n_staking
            ):
                credential.is_unusual_path = True

        elif address_type in (
            CardanoAddressType.POINTER,
            CardanoAddressType.POINTER_SCRIPT,
        ):
            credential.is_other_warning = True

        elif address_type == CardanoAddressType.REWARD:
            if not SCHEMA_STAKING.match(address_params.address_n_staking):
                credential.is_unusual_path = True

        elif address_type in (
            CardanoAddressType.BASE_KEY_SCRIPT,
            CardanoAddressType.BASE_SCRIPT_SCRIPT,
            CardanoAddressType.REWARD_SCRIPT,
        ):
            credential.is_other_warning = True

        elif address_type in (
            CardanoAddressType.ENTERPRISE,
            CardanoAddressType.ENTERPRISE_SCRIPT,
            CardanoAddressType.BYRON,
        ):
            credential.is_no_staking = True

        else:
            raise RuntimeError  # we didn't cover all address types

        return credential

    def should_warn(self) -> bool:
        return any(
            (
                self.is_reward,
                self.is_no_staking,
                self.is_mismatch,
                self.is_unusual_path,
                self.is_other_warning,
            )
        )

    def is_set(self) -> bool:
        return any((self.path, self.key_hash, self.script_hash, self.pointer))

    def get_title(self) -> str:
        if self.path:
            return "path"
        elif self.key_hash:
            return "key hash"
        elif self.script_hash:
            return "script"
        elif self.pointer:
            return "pointer"
        else:
            return ""

    def format(self) -> list[PropertyType]:
        if self.path:
            return [(None, address_n_to_str(self.path))]
        elif self.key_hash:
            hrp = (
                bech32.HRP_KEY_HASH
                if self.type_name == CREDENTIAL_TYPE_PAYMENT
                else bech32.HRP_STAKE_KEY_HASH
            )
            return [(None, bech32.encode(hrp, self.key_hash))]
        elif self.script_hash:
            return [(None, bech32.encode(bech32.HRP_SCRIPT_HASH, self.script_hash))]
        elif self.pointer:
            return [
                (f"Block: {self.pointer.block_index}", None),
                (f"Transaction: {self.pointer.tx_index}", None),
                (f"Certificate: {self.pointer.certificate_index}", None),
            ]
        else:
            return []


def should_show_credentials(
    address_parameters: messages.CardanoAddressParametersType,
) -> bool:
    return not (
        address_parameters.address_type == CardanoAddressType.BASE
        and SCHEMA_PAYMENT.match(address_parameters.address_n)
        and _do_base_address_credentials_match(
            address_parameters.address_n,
            address_parameters.address_n_staking,
        )
    )


def _do_base_address_credentials_match(
    address_n: list[int],
    address_n_staking: list[int],
) -> bool:
    return address_n_staking == _path_to_staking_path(address_n)


def _path_to_staking_path(path: list[int]) -> list[int]:
    return to_account_path(path) + [CHAIN_STAKING_KEY, 0]
