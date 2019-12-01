from trezor.messages.NEM2SignTx import (
    NEM2SignTx,
    NEM2TransactionCommon,
    NEM2TransferTransaction,
)
from trezor.wire import ProcessError

from ..helpers import (
    NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT,
    NEM2_NAMESPACE_REGISTRATION_TYPE_CHILD
)

def _validate_namespace_registration(namespace_registration: NEM2NamespaceRegistrationTransaction, version: int):
    print("VALIDATING", namespace_registration.registration_type)
    if(
        namespace_registration.registration_type != NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT and
        namespace_registration.registration_type != NEM2_NAMESPACE_REGISTRATION_TYPE_CHILD
    ):
        raise ProcessError("Invalid namespace registration type")

