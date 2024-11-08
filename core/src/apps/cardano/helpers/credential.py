from typing import TYPE_CHECKING

from trezor import TR
from trezor.enums import CardanoAddressType

from .paths import SCHEMA_PAYMENT

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
    is_other_warning: bool = False  # TODO: this seems to be unused

    def __init__(
        self,
        type_name: str,
        address_type: CardanoAddressType,
        path: list[int],
        key_hash: bytes | None,
        script_hash: bytes | None,
        pointer: messages.CardanoBlockchainPointerType | None,
    ) -> None:
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
        address_type = address_params.address_type  # local_cache_attribute
        CAT = CardanoAddressType  # local_cache_global

        credential = cls(
            type_name=CREDENTIAL_TYPE_PAYMENT,
            address_type=address_type,
            path=address_params.address_n,
            key_hash=None,
            script_hash=address_params.script_payment_hash,
            pointer=None,
        )

        if address_type in (
            CAT.BASE,
            CAT.BASE_KEY_SCRIPT,
            CAT.POINTER,
            CAT.ENTERPRISE,
            CAT.BYRON,
        ):
            if not SCHEMA_PAYMENT.match(address_params.address_n):
                credential.is_unusual_path = True

        elif address_type in (
            CAT.BASE_SCRIPT_KEY,
            CAT.BASE_SCRIPT_SCRIPT,
            CAT.POINTER_SCRIPT,
            CAT.ENTERPRISE_SCRIPT,
        ):
            credential.is_other_warning = True

        elif address_type in (
            CAT.REWARD,
            CAT.REWARD_SCRIPT,
        ):
            credential.is_reward = True

        else:
            raise RuntimeError  # we didn't cover all address types

        return credential

    @classmethod
    def stake_credential(
        cls, address_params: messages.CardanoAddressParametersType
    ) -> "Credential":
        from .paths import SCHEMA_STAKING

        address_n_staking = address_params.address_n_staking  # local_cache_attribute
        address_type = address_params.address_type  # local_cache_attribute
        CAT = CardanoAddressType  # local_cache_global

        credential = cls(
            type_name=CREDENTIAL_TYPE_STAKE,
            address_type=address_type,
            path=address_n_staking,
            key_hash=address_params.staking_key_hash,
            script_hash=address_params.script_staking_hash,
            pointer=address_params.certificate_pointer,
        )

        if address_type == CAT.BASE:
            if address_params.staking_key_hash:
                credential.is_other_warning = True
            else:
                if not SCHEMA_STAKING.match(address_n_staking):
                    credential.is_unusual_path = True
                if not _do_base_address_credentials_match(
                    address_params.address_n,
                    address_n_staking,
                ):
                    credential.is_mismatch = True

        elif address_type == CAT.BASE_SCRIPT_KEY:
            if address_n_staking and not SCHEMA_STAKING.match(address_n_staking):
                credential.is_unusual_path = True

        elif address_type in (
            CAT.POINTER,
            CAT.POINTER_SCRIPT,
        ):
            credential.is_other_warning = True

        elif address_type == CAT.REWARD:
            if not SCHEMA_STAKING.match(address_n_staking):
                credential.is_unusual_path = True

        elif address_type in (
            CAT.BASE_KEY_SCRIPT,
            CAT.BASE_SCRIPT_SCRIPT,
            CAT.REWARD_SCRIPT,
        ):
            credential.is_other_warning = True

        elif address_type in (
            CAT.ENTERPRISE,
            CAT.ENTERPRISE_SCRIPT,
            CAT.BYRON,
        ):
            credential.is_no_staking = True

        else:
            raise RuntimeError  # we didn't cover all address types

        return credential

    def is_set(self) -> bool:
        return any((self.path, self.key_hash, self.script_hash, self.pointer))

    def get_title(self) -> str:
        if self.path:
            return TR.cardano__path
        elif self.key_hash:
            return TR.cardano__key_hash
        elif self.script_hash:
            return TR.cardano__script
        elif self.pointer:
            return TR.cardano__pointer
        else:
            return ""

    def format(self) -> list[PropertyType]:
        from ...common.paths import address_n_to_str
        from . import bech32

        pointer = self.pointer  # local_cache_attribute

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
        elif pointer:
            return [
                (f"{TR.cardano__block}: {pointer.block_index}", None),
                (f"{TR.cardano__transaction}: {pointer.tx_index}", None),
                (f"{TR.cardano__certificate}: {pointer.certificate_index}", None),
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
    from .paths import CHAIN_STAKING_KEY
    from .utils import to_account_path

    # Note: This checks that the account matches and the staking path address_index is 0.
    # (Even though other values are allowed, we want to display them to the user.)
    path_to_staking_path = to_account_path(address_n) + [CHAIN_STAKING_KEY, 0]
    return address_n_staking == path_to_staking_path
