from trezor.crypto.curve import ed25519
from trezor.messages.HederaSignTx import HederaSignTx
from trezor.messages.StellarSignedTx import HederaSignedTx
from trezor.strings import format_amount

from apps.common import paths
from apps.common.keychain import auto_keychain

from .layout import (
    confirm_account,
    confirm_associate_token,
    confirm_create_account,
    confirm_transfer_hbar,
    confirm_transfer_token,
    format_account,
)

transaction_types = {
    "CONFIRM": "Confirm Account",
    "CREATE": "Create Account",
    "TOKEN": "Token Transfer",
    "HBAR": "Hbar Transfer",
    "ASSOCIATE": "Token Associate",
}


def validate_tx(msg: HederaSignTx) -> str | None:
    if msg.tx is not None:
        # Create Account
        if msg.tx.cryptoCreateAccount is not None:
            # can't be both
            if msg.tx.cryptoTransfer is not None:
                return None

            return transaction_types["CREATE"]

        # Confirm Account, Transfer Hbar, Transfer Token
        if msg.tx.cryptoTransfer is not None:
            # Hbar transfer
            if msg.tx.cryptoTransfer.transfers is not None:
                # but also has token transfers (unsupported)
                if msg.tx.cryptoTransfer.tokenTransfers is not None:
                    return None

                # at most two parties (confirm account, hbar transfer)
                if len(msg.tx.cryptoTransfer.transfers.accountAmounts) > 2:
                    return None

                # between sender and one other account
                if len(msg.tx.cryptoTransfer.transfers.accountAmounts) == 2:
                    return transaction_types["HBAR"]

                # transfer 0 hbar to nobody, with a max fee of 1 tinybar
                # this fails precheck on hedera in a way that signifies whether or not the account
                # used as the operator is associated with the key used to sign this transaction
                if (
                    len(msg.tx.cryptoTransfer.transfers.accountAmounts) == 1
                    and msg.tx.cryptoTransfer.transfers.accountAmounts[0].amount == 0
                    and msg.tx.cryptoTransfer.fee == 1
                ):
                    return transaction_types["CONFIRM"]

            # Token Transfer
            if msg.tx.crytpoTransfer.tokenTransfers is not None:
                # but also has hbar transfers (unsupported)
                if msg.tx.cryptoTransfer.transfers is not None:
                    return None

                # more than one token transfer (unsupported)
                if len(msg.tx.cryptoTransfer.tokenTransfers) >= 1:
                    return None

                # transfer token to multiple parties (unsupported)
                if len(msg.tx.cryptoTransfer.tokenTransfers[0].accountAmounts) > 2:
                    return None

                return transaction_types["TOKEN"]

        if msg.tx.tokenAssociate is not None:
            if (
                msg.tx.tokenAssociate.account is not None
                and len(msg.tx.tokenAssociate.tokens) == 1
            ):
                return transaction_types["ASSOCIATE"]

    return None


async def handle_confirm_account(ctx, msg: HederaSignTx):
    account = format_account(
        msg.tx.cryptoTransfer.transfers.accountAmounts[0].accountID
    )
    await confirm_account(ctx, account)


async def handle_create_account(ctx, msg: HederaSignTx):
    initial_balance = format_amount(msg.tx.cryptoCreateAccount.initialBalance, 8)
    await confirm_create_account(ctx, initial_balance)


async def handle_transfer_hbar(ctx, msg: HederaSignTx):
    await confirm_transfer_hbar(ctx, msg)


async def handle_transfer_token(ctx, msg: HederaSignTx):
    await confirm_transfer_token(ctx, msg)


async def handle_associate_token(ctx, msg: HederaSignTx):
    await confirm_associate_token(ctx, msg)


@auto_keychain(__name__)
async def sign_tx(ctx, msg: HederaSignTx, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    current_tx_type = validate_tx(msg)

    if current_tx_type == transaction_types["CONFIRM"]:
        await handle_confirm_account(ctx, msg)
    elif current_tx_type == transaction_types["CREATE"]:
        await handle_create_account(ctx, msg)
    elif current_tx_type == transaction_types["HBAR"]:
        await handle_transfer_hbar(ctx, msg)
    elif current_tx_type == transaction_types["TOKEN"]:
        await handle_transfer_token(ctx, msg)
    elif current_tx_type == transaction_types["ASSOCIATE"]:
        await handle_associate_token(ctx, msg)
    else:
        raise ("Hedera: Transaction not supported")

    signature = ed25519.sign(node.private_key(), msg.tx)
    return HederaSignedTx(signature=signature)
