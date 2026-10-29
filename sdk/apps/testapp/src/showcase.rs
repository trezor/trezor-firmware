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
            Field::amount("Amount", "1.5 TRX"),
            Field::amount("Fee limit", "10 TRX"),
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
            Field::amount("Amount", "1,000 TRX"),
            Field::text("Resource", "Energy"),
        ],
    )
    .confirm()?;

    let lock: Option<&str> = Some(LOCK_PERIOD);
    let mut facts = Vec::from([
        Field::amount("Amount", "1,000 TRX"),
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
                Field::amount("Value", "1,000 USDT"),
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
