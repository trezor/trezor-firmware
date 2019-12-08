from trezor.messages.NEM2SignTx import (
    NEM2SignTx,
    NEM2TransactionCommon,
)
from trezor.wire import ProcessError

from ..helpers import (
    NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT,
    NEM2_NAMESPACE_REGISTRATION_TYPE_SUB,
    NEM2_ALIAS_ACTION_TYPE_LINK,
    NEM2_ALIAS_ACTION_TYPE_UNLINK,
)

def _validate_namespace_registration(namespace_registration: NEM2NamespaceRegistrationTransaction, version: int):
    if(
        namespace_registration.registration_type != NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT and
        namespace_registration.registration_type != NEM2_NAMESPACE_REGISTRATION_TYPE_SUB
    ):
        raise ProcessError("Invalid namespace registration type")
    if(namespace_registration.registration_type == NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT):
        if(int(namespace_registration.duration) < 1 or int(namespace_registration.duration) > 2102400):
            raise ProcessError("Invalid namespace registration duration")
    if(namespace_registration.registration_type == NEM2_NAMESPACE_REGISTRATION_TYPE_SUB):
        if(namespace_registration.parent_id is None):
            raise ProcessError("Parent Id is required for subnamespace registration")
    #TODO: figure out how to get regex in here, valid characters are a,b,c,…,z,0,1,2,…,9,_ ,-
    if(len(namespace_registration.namespace_name) > 64):
        raise ProcessError("Maximum namespace name is 64 characters")
    if(namespace_registration.id is None):
        raise ProcessError("Id is required")

def _validate_address_alias(address_alias: NEM2AddressAliasTransaction, version: int):
    if(
        address_alias.alias_action != NEM2_ALIAS_ACTION_TYPE_LINK and
        address_alias.alias_action != NEM2_ALIAS_ACTION_TYPE_UNLINK
    ):
        raise ProcessError("Invalid alias action type")

    if(address_alias.address.address is None):
        raise ProcessError("Address is required")

    if(address_alias.namespace_id is None):
        raise ProcessError("Namespace Id is required")



