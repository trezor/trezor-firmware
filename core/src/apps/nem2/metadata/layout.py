from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2NamespaceMetadataTransaction import NEM2NamespaceMetadataTransaction

from trezor.ui.text import Text
from trezor.utils import format_amount
from trezor.ui.scroll import Paginated
from ubinascii import unhexlify

from ..layout import require_confirm_final, require_confirm_text

from apps.common.confirm import require_confirm
from apps.common.layout import split_address

async def ask_namespace_metadata(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    namespace_metadata: NEM2NamespaceMetadataTransaction,
    embedded=False
):

    properties = []
    # confirm target public key
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Target Public Key:")
    t.mono(*split_address(namespace_metadata.target_public_key.upper()))
    properties.append(t)

    # confirm namespace id and metadata key
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Namespace Id:")
    t.normal(namespace_metadata.target_namespace_id.upper())
    t.bold("Metadata Key:")
    t.normal(namespace_metadata.scoped_metadata_key)
    properties.append(t)

    # confirm new value
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Metadata Value:")
    t.normal(unhexlify(namespace_metadata.value).decode())
    properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

    if not embedded:
        await require_confirm_final(ctx, common.max_fee)