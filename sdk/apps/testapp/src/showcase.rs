//! The API reference's examples, one device flow per example, so the real
//! firmware can draw every one of them.
//!
//! The host picks a flow by name ([`show`]); the flow then runs on the device
//! exactly as the reference writes it, with the reference's sample values in place
//! of its parameters. Nothing here is a host-side mock: the host asks, the device
//! draws.

use core::fmt::Write as _;

use trezor_app_sdk::crypto::{self as sdk, HasherExt, HashingAlgorithm};
use trezor_app_sdk::modui::{self, Details, Extra, Field};
use trezor_app_sdk::{Error, Result};

use crate::alloc_types::{String, Vec};
use crate::proto::testapp::{self as wire, ui_result::Reply};

// The sample values the reference's examples pass in.
const RECIPIENT: &str = "TQ9JfxgJ9JBz4GZ4MRDrjJeBdA6Mx5yYhq";
const OWNER: &str = "TQrY8tryqsYVCYS3MFbtffiPp2ccyn4STm";
const CONTRACT: &str = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t";
const ACCOUNT: &str = "TRX #1";
const LOCK_PERIOD: &str = "3 days";
const PATH: &str = "m/44'/195'/0'/0/0";
const TXID: &str = "8f2b6c1d9e4a7f30b5c2e81d6a9f4b7c3e0d5a2f8b6c1e9d4a7f3b0c5e2d81a6";
const XPUB: &str = "tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkkfHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U";
const CALLDATA: [u8; 68] = [
    // `transfer(address,uint256)` and its two arguments.
    0xa9, 0x05, 0x9c, 0xbb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x41, 0x3f, 0x5d, 0x7a, 0x1b, 0x2c, 0x4d, 0x5e, 0x6f, 0x70, 0x81, 0x92, 0xa3, 0xb4, 0xc5, 0xd6,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x64,
];

/// Runs the flow named by the request, and answers with how it ended.
pub fn show(m: wire::Showcase) -> Result<wire::UiResult> {
    let flow: fn() -> Result<()> = match m.name.as_str() {
        "send" => send,
        "delegate" => delegate,
        "claim-owner" => claim_owner,
        "unknown-contract" => unknown_contract,
        "path-warning" => path_warning,
        "typed-data" => typed_data,
        "get-address" => get_address,
        "get-pubkey" => get_pubkey,
        "contract-data" => contract_data,
        "consent" => consent,
        "swap" => swap,
        "fee-bump" => fee_bump,
        "sign-message" => sign_message,
        "verify-message" => verify_message,
        "signing-progress" => signing_progress,
        _ => return Err(Error::InvalidArgument),
    };
    match flow() {
        Ok(()) => answer(Reply::Confirmed),
        Err(e) if e.code() == Error::Cancelled.code() => answer(Reply::Cancelled),
        Err(e) => Err(e),
    }
}

/// The reference's "Tron send, before and after": two reviews, the second one
/// the last yes before signing.
fn send() -> Result<()> {
    let account = [
        Field::text("Account", ACCOUNT),
        Field::text("Derivation path", PATH),
    ];
    modui::review("send", "Send", &[Field::address("Recipient", RECIPIENT)])
        .extras(&[Extra::new("Account info", &account)])
        .confirm()?;
    modui::review(
        "summary",
        "Send",
        &[
            Field::amount("Amount", "1.5", "TRX"),
            Field::amount("Fee limit", "10", "TRX"),
        ],
    )
    .extras(&[Extra::new("Account info", &account)])
    .confirm_final()
}

/// The reference's `delegate` examples: several facts on one screen, then the
/// last yes with an optional fact still last.
fn delegate() -> Result<()> {
    modui::review(
        "delegate",
        "Delegate",
        &[
            Field::address("Recipient", RECIPIENT),
            Field::amount("Amount", "1,000", "TRX"),
            Field::text("Resource", "Energy"),
        ],
    )
    .confirm()?;

    let lock: Option<&str> = Some(LOCK_PERIOD);
    let mut facts = Vec::from([
        Field::amount("Amount", "1,000", "TRX"),
        Field::text("Resource", "Energy"),
    ]);
    if let Some(lock) = lock {
        facts.push(Field::text("Lock period", lock));
    }
    modui::review("delegate/final", "Delegate", &facts).confirm_final()
}

/// The reference's "a warning inside a review".
fn claim_owner() -> Result<()> {
    modui::review(
        "claim/owner",
        "Claim",
        &[
            Field::address("Owner address", OWNER),
            Field::warning("This address is not yours."),
        ],
    )
    .confirm()
}

/// The reference's `danger` example for an unknown contract.
fn unknown_contract() -> Result<()> {
    modui::review(
        "unknown_contract",
        "Important",
        &[
            Field::note("This contract is unknown. Continue only if you trust it."),
            Field::address("Contract", CONTRACT),
        ],
    )
    .confirm_danger()
}

/// The reference's `danger` example for an unusual path.
fn path_warning() -> Result<()> {
    modui::review(
        "path_warning",
        "Unknown path",
        &[
            Field::note("This path is not usual for this coin."),
            Field::text("Derivation path", PATH),
        ],
    )
    .confirm_danger()
}

/// The reference's EIP-712 example: the person may skip the details, and the
/// app walks the message itself when they do not.
fn typed_data() -> Result<()> {
    match modui::details(
        "typed_data/message",
        "Confirm message",
        &[
            Field::text("Type", "Permit"),
            Field::text("Contains", "owner, spender, value, deadline"),
        ],
    )? {
        Details::Show => modui::review(
            "typed_data/owner",
            "Confirm message",
            &[
                Field::address("Owner", OWNER),
                Field::amount("Value", "1,000", "USDT"),
            ],
        )
        .confirm(),
        Details::Skip => Ok(()),
    }
}

/// The reference's `verify_address` example.
fn get_address() -> Result<()> {
    modui::verify_address("address", RECIPIENT, Some(ACCOUNT), Some(PATH))
}

/// The reference's `verify_pubkey` example.
fn get_pubkey() -> Result<()> {
    modui::verify_pubkey("pubkey", XPUB, Some(ACCOUNT), Some(PATH))
}

/// The reference's `Field::data` example: the raw bytes of a contract call.
fn contract_data() -> Result<()> {
    modui::review(
        "contract/data",
        "Contract data",
        &[
            Field::address("Contract", CONTRACT),
            Field::data("Input data", &CALLDATA),
        ],
    )
    .confirm()
}

/// A question the person answers yes or no: there is no value to check.
fn consent() -> Result<()> {
    modui::review(
        "stake/consent",
        "Stake",
        &[Field::note(
            "Stake your TRX with Everstake? You can unstake at any time.",
        )],
    )
    .confirm()
}

/// A swap: what leaves, what arrives and where, as the last yes before signing.
/// An extra the trade doesn't have is not offered.
fn swap() -> Result<()> {
    // The host's refund address, already checked with check_address_mac.
    let refund: Option<Field> = Some(Field::address("Refund address", OWNER));
    let provider = [
        Field::text("Provider", "Changelly"),
        Field::text("Quote ID", "a3f9-77c1"),
    ];
    let fees = [
        Field::amount("Provider fee", "0.50", "USDC"),
        Field::amount("Fee limit", "10", "TRX"),
    ];
    let route = [
        Field::text("Hop 1", "TRX to USDT on SunSwap"),
        Field::text("Hop 2", "USDT to USDC on Curve"),
    ];
    let account = [
        Field::text("Account", ACCOUNT),
        Field::text("Derivation path", PATH),
    ];
    modui::review(
        "swap",
        "Swap",
        &[
            Field::amount("You pay", "-1,000", "TRX"),
            Field::amount("You receive", "+118.40", "USDC"),
            Field::address("Recipient", RECIPIENT),
            Field::amount("Network fee", "1.2", "TRX"),
            Field::warning("The price impact is 4.2%."),
        ],
    )
    .extras(&[
        Extra::new("Provider", &provider),
        Extra::new("Refund", refund.as_slice()), // None: not offered
        Extra::new("Fee details", &fees),
        Extra::new("Route", &route),
        Extra::new("Account info", &account),
    ])
    .confirm_final()
}

/// Raising the fee of a transaction already sent (replace-by-fee).
fn fee_bump() -> Result<()> {
    let rates = [
        Field::text("Old fee rate", "4 sat/vB"),
        Field::text("New fee rate", "12 sat/vB"),
    ];
    modui::review(
        "bump_fee",
        "Bump fee",
        &[
            Field::address("Transaction ID", TXID),
            Field::amount("Old fee", "0.00000564", "BTC"),
            Field::amount("New fee", "0.00001692", "BTC"),
            Field::amount("Increased by", "0.00001128", "BTC"),
        ],
    )
    .extras(&[Extra::new("Fee rate", &rates)])
    .confirm_final()
}

/// Signing a message: the address that signs, then the message, as the last
/// yes. Bytes that are not UTF-8 are data, not text.
fn sign_message() -> Result<()> {
    let message: &[u8] = b"Log in to example.com at 18:05";
    let shown = match core::str::from_utf8(message) {
        Ok(text) => Field::text("Message", text),
        Err(_) => Field::data("Message", message),
    };
    modui::review(
        "sign_message",
        "Sign message",
        &[Field::address("Address", RECIPIENT), shown],
    )
    .confirm_final()
}

/// Verifying a message. The app checks the signature before it asks, so an
/// invalid one never reaches the screen.
fn verify_message() -> Result<()> {
    modui::review(
        "verify_message",
        "Verify message",
        &[
            Field::address("Address", RECIPIENT),
            Field::text("Message", "Log in to example.com at 18:05"),
        ],
    )
    .confirm()?;
    modui::done("verify_message/valid", "The signature is valid");
    Ok(())
}

/// The reference's `progress` examples: work the app cannot count, then counted
/// work whose label changes per step, then the `done` screen that ends the flow.
/// The work hashes each input, since the testapp has no transaction to sign.
fn signing_progress() -> Result<()> {
    let inputs: [&[u8]; 3] = [&b"input 1"[..], &b"input 2"[..], &b"input 3"[..]];
    // Work the app cannot count: the bar shows motion, not a fill.
    let mut hasher = modui::progress("Preparing", None, |_| {
        sdk::get_hasher(HashingAlgorithm::Sha256)
    });
    modui::progress("Signing", Some(inputs.len() as u32), |progress| {
        for (i, input) in inputs.iter().enumerate() {
            let mut label = String::new();
            let _ = write!(label, "Signing input {}/{}", i + 1, inputs.len());
            progress.label(&label);
            hasher.update(input);
            progress.step(1);
        }
    });
    modui::done("signed", "Transaction signed");
    Ok(())
}

fn answer(reply: Reply) -> Result<wire::UiResult> {
    Ok(wire::UiResult {
        reply: reply as i32,
    })
}
