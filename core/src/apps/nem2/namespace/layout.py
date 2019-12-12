from trezor import ui

from trezor.messages import ButtonRequestType
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2NamespaceRegistrationTransaction import NEM2NamespaceRegistrationTransaction
from trezor.messages.NEM2AddressAliasTransaction import NEM2AddressAliasTransaction
from trezor.messages.NEM2MosaicAliasTransaction import NEM2MosaicAliasTransaction

from trezor.ui.text import Text
from trezor.ui.scroll import Paginated

from ..helpers import (
    NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT,
    NEM2_NAMESPACE_REGISTRATION_TYPE_SUB,
    NEM2_ALIAS_ACTION_TYPE_LINK,
    NEM2_ALIAS_ACTION_TYPE_UNLINK,
)
from ..layout import require_confirm_final

from apps.common.confirm import require_confirm
from apps.common.layout import split_address

async def ask_namespace_registration(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    namespace_registration: NEM2NamespaceRegistrationTransaction,
    embedded=False
):
    # confirm name and id
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Id:")
    t.br()
    t.normal(namespace_registration.id.upper())
    t.bold("Name:")
    t.br()
    t.normal(namespace_registration.namespace_name)
    properties.append(t)

    # confirm registration type and either parentId and  and id
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Registration Type:")
    t.br()
    if(namespace_registration.registration_type == NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT):
        t.normal("Root Namespace")
        t.bold("Duration:")
        t.br()
        t.normal(namespace_registration.duration)
    elif (namespace_registration.registration_type == NEM2_NAMESPACE_REGISTRATION_TYPE_SUB):
        t.normal("Sub Namespace")
        t.bold("Parent Id:")
        t.br()
        t.normal(namespace_registration.parent_id.upper())
    properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

    if not embedded:
        await require_confirm_final(ctx, common.max_fee)

async def ask_address_alias(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    address_alias: NEM2NamespaceRegistrationTransaction,
    embedded=False
):
    # confirm namespace id
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Namspace Id:")
    t.br()
    t.normal(address_alias.namespace_id.upper())
    t.bold("Alias Action:")
    t.br()
    if(address_alias.alias_action == NEM2_ALIAS_ACTION_TYPE_LINK):
        t.normal("LINK")
    elif (address_alias.alias_action == NEM2_ALIAS_ACTION_TYPE_UNLINK):
        t.normal("UNLINK")

    properties.append(t)
    paginated = Paginated(properties)

    # confirm address to link/unlink
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Address:")
    t.br()
    t.mono(*split_address(address_alias.address.address))

    properties.append(t)
    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

    if not embedded:
        await require_confirm_final(ctx, common.max_fee)

async def ask_mosaic_alias(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    mosaic_alias: NEM2MosaicAliasTransaction,
    embedded=False
):
    await require_confirm_properties(ctx, mosaic_alias)
    if not embedded:
        await require_confirm_final(ctx, common.max_fee)

async def require_confirm_properties(ctx, mosaic_alias: NEM2MosaicAliasTransaction):
    properties = []

    # Mosaic ID
    if mosaic_alias.mosaic_id:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Mosaic Id:")
        t.br()
        t.normal(mosaic_alias.mosaic_id)
        properties.append(t)

    # Namespace ID
    if mosaic_alias.namespace_id:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Namespace Id:")
        t.br()
        t.normal(mosaic_alias.namespace_id)
        properties.append(t)
    # Alias Action
    if (mosaic_alias.alias_action == NEM2_ALIAS_ACTION_TYPE_LINK or
        mosaic_alias.alias_action == NEM2_ALIAS_ACTION_TYPE_UNLINK):
        alias_text = "Link" if mosaic_alias.alias_action else "Unlink"
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Alias Action:")
        t.br()
        t.normal('{} ({})'.format(alias_text, mosaic_alias.alias_action))
        properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)
