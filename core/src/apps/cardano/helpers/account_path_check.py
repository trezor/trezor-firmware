from typing import TYPE_CHECKING

from trezor.wire import ProcessError

from .. import seed

if TYPE_CHECKING:
    from trezor.messages import (
        CardanoPoolOwner,
        CardanoTxCertificate,
        CardanoTxOutput,
        CardanoTxWithdrawal,
        CardanoTxWitnessRequest,
    )


class AccountPathChecker:
    """
    Used to verify that all paths in a transaction which are not being shown to the user belong
    to the same account. Paths are matched against the path which is added first. If there's a mismatch,
    an error is raised.
    """

    UNDEFINED = object()

    def __init__(self) -> None:
        self.account_path: object | list[int] = self.UNDEFINED

    def _add(self, path: list[int], error: ProcessError) -> None:
        from .utils import to_account_path

        # multi-sig and minting paths are always shown and thus don't need to be checked
        if seed.is_multisig_path(path) or seed.is_minting_path(path):
            return

        account_path = to_account_path(path)
        if self.account_path is self.UNDEFINED:
            self.account_path = account_path
        elif (
            self.account_path != account_path
            and not self._is_byron_and_shelley_equivalent(account_path)
        ):
            raise error

    def _is_byron_and_shelley_equivalent(self, account_path: list[int]) -> bool:
        """
        For historical purposes Byron path (44'/1815'/0') is considered equivalent to the Shelley
        path with the same account (1852'/1815'/0'). This combination of accounts is allowed
        in order to make Byron to Shelley migrations possible with the Shelley path staying hidden
        from the user. This way the user can be sure that the funds are being moved between the user's
        accounts without being bothered by more screens.
        """
        from ...common.paths import HARDENED
        from .paths import ACCOUNT_PATH_INDEX, ACCOUNT_PATH_LENGTH

        self_account_path = self.account_path  # local_cache_attribute

        assert isinstance(self_account_path, list)
        is_control_path_byron_or_shelley = seed.is_byron_path(
            self_account_path
        ) or seed.is_shelley_path(self_account_path)

        is_new_path_byron_or_shelley = seed.is_byron_path(
            account_path
        ) or seed.is_shelley_path(account_path)

        return (
            is_control_path_byron_or_shelley
            and is_new_path_byron_or_shelley
            and len(self_account_path) == ACCOUNT_PATH_LENGTH
            and len(account_path) == ACCOUNT_PATH_LENGTH
            and self_account_path[ACCOUNT_PATH_INDEX] == 0 | HARDENED
            and account_path[ACCOUNT_PATH_INDEX] == 0 | HARDENED
        )

    def add_output(self, output: CardanoTxOutput) -> None:
        if not output.address_parameters:
            return

        if not output.address_parameters.address_n:
            return

        self._add(output.address_parameters.address_n, ProcessError("Invalid output"))

    def add_certificate(self, certificate: CardanoTxCertificate) -> None:
        if not certificate.path:
            return

        self._add(certificate.path, ProcessError("Invalid certificate"))

    def add_pool_owner(self, pool_owner: CardanoPoolOwner) -> None:
        if not pool_owner.staking_key_path:
            return

        self._add(pool_owner.staking_key_path, ProcessError("Invalid certificate"))

    def add_withdrawal(self, withdrawal: CardanoTxWithdrawal) -> None:
        if not withdrawal.path:
            return

        self._add(withdrawal.path, ProcessError("Invalid withdrawal"))

    def add_witness_request(self, witness_request: CardanoTxWitnessRequest) -> None:
        self._add(witness_request.path, ProcessError("Invalid witness request"))
