"""The example flows, composed on the host from the app's modui endpoints.

An app shows a flow as a series of screens, and the testapp exposes one endpoint
per screen, so the host picks the facts and the order. Each function here is one
flow an app would show, with sample values in place of a real transaction's, so
every screen of the library can be walked end to end.

A flow stops as soon as the person backs out of a screen: `_confirm` raises
`Cancelled`, and `run` answers `Cancelled` for the whole flow.
"""

from __future__ import annotations

import hashlib

from trezorlib import protobuf

from . import messages as m
from .client import TestApp, address, amount, data, extras, note, text, warning

# The sample values the flows pass in.
RECIPIENT = "TQ9JfxgJ9JBz4GZ4MRDrjJeBdA6Mx5yYhq"
OWNER = "TQrY8tryqsYVCYS3MFbtffiPp2ccyn4STm"
CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
ACCOUNT = "TRX #1"
LOCK_PERIOD = "3 days"
PATH = "m/44'/195'/0'/0/0"
TXID = "8f2b6c1d9e4a7f30b5c2e81d6a9f4b7c3e0d5a2f8b6c1e9d4a7f3b0c5e2d81a6"
XPUB = (
    "tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkk"
    "fHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U"
)
MESSAGE = b"Log in to example.com at 18:05"

# `transfer(address,uint256)` and its two arguments.
CALLDATA = bytes.fromhex(
    "a9059cbb"
    "000000000000000000000000"
    "413f5d7a1b2c4d5e6f708192a3b4c5d6"
    "00000000000000000000000000000000"
    "00000000000000000000000000000000"
    "00000064"
)


class Cancelled(Exception):
    """The person backed out of a screen, so the flow ended there."""


def _confirm(app: TestApp, request: protobuf.MessageType) -> None:
    """Send one request, and stop the flow if the person backs out."""
    if app.call(request) is m.Reply.Cancelled:
        raise Cancelled


# ============================================================================
# Flows
# ============================================================================


def send(app: TestApp) -> None:
    """A transfer: a review of the recipient, then the summary as the last yes
    before signing, then the closing screen."""
    account = [
        text("Account", ACCOUNT),
        text("Derivation path", PATH),
    ]
    _confirm(
        app,
        m.Review(
            step="send",
            title="Send",
            fields=[address("Recipient", RECIPIENT)],
            extras=extras(("Account info", account)),
        ),
    )
    _confirm(
        app,
        m.Summary(
            step="summary",
            title="Send",
            amount=m.Amount(label="Amount", value="1.5", ticker="TRX"),
            fee=m.Amount(label="Fee limit", value="10", ticker="TRX"),
            account=m.Extra(label="Account info", fields=account),
        ),
    )
    _confirm(app, m.Done(step="send/done", text="Transaction sent"))


def delegate(app: TestApp) -> None:
    """Delegating resources: several facts on one screen, then the last yes with
    an optional fact still last, then the closing screen."""
    _confirm(
        app,
        m.Review(
            step="delegate",
            title="Delegate",
            fields=[
                address("Recipient", RECIPIENT),
                amount("Amount", "1,000", "TRX"),
                text("Resource", "Energy"),
            ],
        ),
    )

    lock_period: str | None = LOCK_PERIOD
    facts = [
        amount("Amount", "1,000", "TRX"),
        text("Resource", "Energy"),
    ]
    if lock_period is not None:
        facts.append(text("Lock period", lock_period))
    _confirm(
        app,
        m.Review(
            step="delegate/final",
            title="Delegate",
            fields=facts,
            answer=m.Answer.Strong,
        ),
    )
    _confirm(app, m.Done(step="delegate/done", text="Delegation confirmed"))


def claim_owner(app: TestApp) -> None:
    """A warning inside a review: the owner of the funds is not the signer."""
    _confirm(
        app,
        m.Review(
            step="claim/owner",
            title="Claim",
            fields=[
                address("Owner address", OWNER),
                warning("This address is not yours."),
            ],
        ),
    )


def unknown_contract(app: TestApp) -> None:
    """A danger: a contract the app does not know."""
    _confirm(
        app,
        m.Review(
            step="unknown_contract",
            title="Important",
            fields=[
                note("This contract is unknown. Continue only if you trust it."),
                address("Contract", CONTRACT),
            ],
            answer=m.Answer.Danger,
        ),
    )


def path_warning(app: TestApp) -> None:
    """A danger: a derivation path unusual for the coin."""
    _confirm(
        app,
        m.Review(
            step="path_warning",
            title="Unknown path",
            fields=[
                note("This path is not usual for this coin."),
                text("Derivation path", PATH),
            ],
            answer=m.Answer.Danger,
        ),
    )


def typed_data(app: TestApp) -> None:
    """Typed data (EIP-712): the person may skip the details, and the host
    walks the message itself when they ask for them."""
    reply = app.call(
        m.Review(
            step="typed_data/message",
            title="Confirm message",
            fields=[
                text("Type", "Permit"),
                text("Contains", "owner, spender, value, deadline"),
            ],
            answer=m.Answer.Details,
        )
    )
    if reply is m.Reply.Cancelled:
        raise Cancelled
    if reply is m.Reply.ShowDetails:
        _confirm(
            app,
            m.Review(
                step="typed_data/owner",
                title="Confirm message",
                fields=[
                    address("Owner", OWNER),
                    amount("Value", "1,000", "USDT"),
                ],
            ),
        )


def get_address(app: TestApp) -> None:
    """One of the person's own addresses."""
    _confirm(
        app,
        m.VerifyAddress(step="address", value=RECIPIENT, account=ACCOUNT, path=PATH),
    )


def get_pubkey(app: TestApp) -> None:
    """One of the person's own public keys."""
    _confirm(
        app,
        m.VerifyPubkey(step="pubkey", value=XPUB, account=ACCOUNT, path=PATH),
    )


def contract_data(app: TestApp) -> None:
    """The raw bytes of a contract call, as a `data` field."""
    _confirm(
        app,
        m.Review(
            step="contract/data",
            title="Contract data",
            fields=[
                address("Contract", CONTRACT),
                data("Input data", CALLDATA),
            ],
        ),
    )


def consent(app: TestApp) -> None:
    """A question the person answers yes or no: there is no value to check."""
    _confirm(
        app,
        m.Review(
            step="stake/consent",
            title="Stake",
            fields=[
                note("Stake your TRX with Everstake? You can unstake at any time.")
            ],
        ),
    )


def swap(app: TestApp) -> None:
    """A swap: what leaves, what arrives and where, as the last yes before
    signing. An extra the trade doesn't have is not offered."""
    refund: str | None = OWNER
    provider = [
        text("Provider", "Changelly"),
        text("Quote ID", "a3f9-77c1"),
    ]
    fees = [
        amount("Provider fee", "0.50", "USDC"),
        amount("Fee limit", "10", "TRX"),
    ]
    route = [
        text("Hop 1", "TRX to USDT on SunSwap"),
        text("Hop 2", "USDT to USDC on Curve"),
    ]
    account = [
        text("Account", ACCOUNT),
        text("Derivation path", PATH),
    ]

    items = [("Provider", provider)]
    if refund is not None:
        items.append(("Refund", [address("Refund address", refund)]))
    items += [
        ("Fee details", fees),
        ("Route", route),
        ("Account info", account),
    ]

    _confirm(
        app,
        m.Review(
            step="swap",
            title="Swap",
            fields=[
                amount("You pay", "-1,000", "TRX"),
                amount("You receive", "+118.40", "USDC"),
                address("Recipient", RECIPIENT),
                amount("Network fee", "1.2", "TRX"),
                warning("The price impact is 4.2%."),
            ],
            extras=extras(*items),
            answer=m.Answer.Strong,
        ),
    )
    _confirm(app, m.Done(step="swap/done", text="Swap confirmed"))


def fee_bump(app: TestApp) -> None:
    """Raising the fee of a transaction already sent (replace-by-fee)."""
    rates = [
        text("Old fee rate", "4 sat/vB"),
        text("New fee rate", "12 sat/vB"),
    ]
    _confirm(
        app,
        m.Review(
            step="bump_fee",
            title="Bump fee",
            fields=[
                address("Transaction ID", TXID),
                amount("Old fee", "0.00000564", "BTC"),
                amount("New fee", "0.00001692", "BTC"),
                amount("Increased by", "0.00001128", "BTC"),
            ],
            extras=extras(("Fee rate", rates)),
            answer=m.Answer.Strong,
        ),
    )
    _confirm(app, m.Done(step="bump_fee/done", text="Transaction replaced"))


def sign_message(app: TestApp) -> None:
    """Signing a message: the address that signs, then the message, as the last
    yes. Bytes that are not UTF-8 are data, not text."""
    try:
        shown = text("Message", MESSAGE.decode())
    except UnicodeDecodeError:
        shown = data("Message", MESSAGE)
    _confirm(
        app,
        m.Review(
            step="sign_message",
            title="Sign message",
            fields=[address("Address", RECIPIENT), shown],
            answer=m.Answer.Strong,
        ),
    )
    _confirm(app, m.Done(step="sign_message/done", text="Message signed"))


def verify_message(app: TestApp) -> None:
    """Verifying a message. The host checks the signature before it asks, so an
    invalid one never reaches the screen."""
    _confirm(
        app,
        m.Review(
            step="verify_message",
            title="Verify message",
            fields=[
                address("Address", RECIPIENT),
                text("Message", MESSAGE.decode()),
            ],
        ),
    )
    _confirm(
        app,
        m.Done(step="verify_message/valid", text="The signature is valid"),
    )


def signing_progress(app: TestApp) -> None:
    """Progress: work the host cannot count, then counted work whose label changes
    per step, then the closing screen. The host hashes each input, since there is
    no transaction to sign."""
    inputs = (b"input 1", b"input 2", b"input 3")

    # Work the host cannot count: the bar shows motion, not a fill.
    with app.progress("Preparing"):
        hasher = hashlib.sha256()

    with app.progress("Signing", total=len(inputs)) as progress:
        for i, chunk in enumerate(inputs, start=1):
            progress.label(f"Signing input {i}/{len(inputs)}")
            hasher.update(chunk)
            progress.step()

    _confirm(app, m.Done(step="signed", text="Transaction signed"))


# Every showcase, by the name `testappctl showcase` takes.
FLOWS = {
    "send": send,
    "delegate": delegate,
    "claim-owner": claim_owner,
    "unknown-contract": unknown_contract,
    "path-warning": path_warning,
    "typed-data": typed_data,
    "get-address": get_address,
    "get-pubkey": get_pubkey,
    "contract-data": contract_data,
    "consent": consent,
    "swap": swap,
    "fee-bump": fee_bump,
    "sign-message": sign_message,
    "verify-message": verify_message,
    "signing-progress": signing_progress,
}

# The single source of truth for the names, in the order the CLI lists them.
SHOWCASES = tuple(FLOWS)


def run(app: TestApp, name: str) -> m.Reply:
    """Run the flow `name` on `app`, and answer how the whole flow ended."""
    try:
        FLOWS[name](app)
    except Cancelled:
        return m.Reply.Cancelled
    return m.Reply.Confirmed
