from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    NEM2Mosaic,
    NEM2TransactionCommon,
    NEM2TransferTransaction,
)
from trezor.ui.text import Text
from trezor.utils import format_amount

from ..helpers import (
    NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT,
    NEM2_NAMESPACE_REGISTRATION_TYPE_CHILD
)
from ..layout import require_confirm_final, require_confirm_text
from ..mosaic.helpers import get_mosaic_definition, is_nem_xem_mosaic

from apps.common.confirm import require_confirm
from apps.common.layout import split_address

async def ask_namespace_registration(
    ctx, common: NEM2TransactionCommon, namespace_registration: NEM2NamespaceRegistrationTransaction
):

    # confirm name and id
    msg = Text("Register Namespace")
    msg.normal("Id:")
    msg.bold(hex(namespace_registration.id)[1:].upper())
    msg.normal("Name:")
    msg.bold(bytes(namespace_registration.namespace_name).decode()) # casting to bytes prevents errors on long names
    await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

    # confirm registration type and either parentId and  and id
    msg = Text("Register Namespace")
    msg.normal("Registration Type:")
    if(namespace_registration.registration_type == NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT):
        msg.bold("Root Namespace")
        msg.normal("Duration:")
        msg.bold(str(namespace_registration.duration)) # casting to bytes prevents errors on long names
    elif (namespace_registration.registration_type == NEM2_NAMESPACE_REGISTRATION_TYPE_CHILD):
        msg.bold("Sub Namespace")
        msg.normal("Parent Id:")
        msg.bold(hex(namespace_registration.parent_id)[1:].upper()) # casting to bytes prevents errors on long names
    await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)
