from trezor import ui

from trezor.messages import ButtonRequestType
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2SecretLockTransaction import NEM2SecretLockTransaction

from trezor.ui.text import Text
from trezor.ui.scroll import Paginated

from ..helpers import (
    NEM2_SECRET_LOCK_SHA3_256,
    NEM2_SECRET_LOCK_KECCAK_256,
    NEM2_SECRET_LOCK_HASH_160,
    NEM2_SECRET_LOCK_HASH_256
)
from ..layout import require_confirm_final

from apps.common.confirm import require_confirm
from apps.common.layout import split_address

enum_to_friendly_text = {
    NEM2_SECRET_LOCK_SHA3_256: "SHA-3 256",
    NEM2_SECRET_LOCK_KECCAK_256: "Keccak 256",
    NEM2_SECRET_LOCK_HASH_160: "Hash 160",
    NEM2_SECRET_LOCK_HASH_256: "Hash 256"
}

async def ask_secret_lock(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    secret_lock: NEM2SecretLockTransaction,
    embedded=False
):
    await require_confirm_properties_lock(ctx, secret_lock)
    if not embedded:
        await require_confirm_final(ctx, common.max_fee)

async def ask_secret_proof(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    secret_proof: NEM2SecretProofTransaction,
    embedded=False
):
    await require_confirm_properties_proof(ctx, secret_proof)
    if not embedded:
        await require_confirm_final(ctx, common.max_fee)

async def require_confirm_properties_lock(ctx, secret_lock: NEM2SecretLockTransaction):
    properties = []
    # Mosaic
    if secret_lock.mosaic:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Mosaic Id:")
        t.normal(secret_lock.mosaic.id)
        t.br()
        t.bold("Amount:")
        t.normal(secret_lock.mosaic.amount)
        properties.append(t)
    # Duration
    if secret_lock.duration:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Duration:")
        t.normal(str(secret_lock.duration))
        properties.append(t)
    # Recipient address
    if secret_lock.recipient_address:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Recipient address:")
        t.mono(*split_address(secret_lock.recipient_address.address))
        properties.append(t)
    # Hash Algorithm
    if secret_lock.hash_algorithm in enum_to_friendly_text:
        friendly_text = enum_to_friendly_text[secret_lock.hash_algorithm]
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=True, max_lines=10)
        t.bold("Hash algorithm used:")
        t.normal('{} ({})'.format(friendly_text, secret_lock.hash_algorithm))
        properties.append(t)
    # Secret
    if secret_lock.secret:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=True, max_lines=10)
        t.bold("Secret:")
        t.mono(*split_address(secret_lock.secret))
        properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

async def require_confirm_properties_proof(ctx, secret_proof: NEM2SecretProofTransaction):
    properties = []
    # Recipient address
    if secret_proof.recipient_address:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Recipient address:")
        t.mono(*split_address(secret_proof.recipient_address.address))
        properties.append(t)
    # Hash Algorithm
    if secret_proof.hash_algorithm in enum_to_friendly_text:
        friendly_text = enum_to_friendly_text[secret_proof.hash_algorithm]
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=True, max_lines=10)
        t.bold("Hash algorithm used:")
        t.normal('{} ({})'.format(friendly_text, secret_proof.hash_algorithm))
        properties.append(t)
    # Secret
    if secret_proof.secret:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=True, max_lines=10)
        t.bold("Secret:")
        t.mono(*split_address(secret_proof.secret))
        properties.append(t)
    # Proof
    if secret_proof.secret:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=True, max_lines=10)
        t.bold("Proof:")
        t.mono(*split_address(secret_proof.proof))
        properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)
