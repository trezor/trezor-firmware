from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    NEM2Mosaic,
    NEM2TransactionCommon,
    NEM2NamespaceMetadataTransaction,
)
from trezor.ui.text import Text
from trezor.utils import format_amount
from ubinascii import unhexlify

from ..layout import require_confirm_final, require_confirm_text

from apps.common.confirm import require_confirm
from apps.common.layout import split_address

async def ask_namespace_metadata(
    ctx, common: NEM2TransactionCommon, namespace_metadata: NEM2NamespaceMetadataTransaction
):

    # confirm target public key
    msg = Text("Namespace Metadata")
    msg.normal("Target Public Key:")
    msg.mono(*split_address(namespace_metadata.target_public_key.upper()))
    await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

    # confirm namespace id and metadata key
    msg = Text("Namespace Metadata")
    msg.normal("Namespace Id:")
    msg.bold(namespace_metadata.target_namespace_id.upper())
    msg.normal("Metadata Key:")
    msg.bold(namespace_metadata.scoped_metadata_key)
    await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)


    # confirm new value
    msg = Text("Namespace Metadata")
    msg.normal("Metadata Value:")
    msg.bold(unhexlify(namespace_metadata.value).decode())
    await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)
