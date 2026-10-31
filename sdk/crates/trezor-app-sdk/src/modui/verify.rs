//! The person's own address or public key. The public docs live on
//! [`verify_address`] and [`verify_pubkey`].
//!
//! Both send one request, and core draws the whole flow around it: the value,
//! its QR code, the account and path, the "does not match" screen and the
//! "confirmed" message. The app sees one answer.

use crate::Result;
use crate::modui::call::{call, yes_or_no};
use crate::structs::{TrezorUiEnum, VerifyRequest};

/// Shows the person an address of theirs to check against the host, and waits
/// for the answer.
///
/// Core adds the QR code, the account and path, the "does not match" screen and
/// the "confirmed" message, as core's own `show_address` does.
///
/// - `step` — the step name, relative to the app, such as `"address"`; see
///   [step names](crate::modui#step-names).
/// - `address` — the address, as the host will show it.
/// - `account` — the account's name, such as `"TRX #1"`.
/// - `path` — the derivation path.
///
/// WIP: multisig addresses are not supported: the request has no slot for the
/// cosigners' xpubs, which core's `show_address` shows.
///
/// `Ok(())`: it matches. `Err(`[`crate::Error::Cancelled`]`)`: it does not, or
/// the person refused.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui;
///
/// fn verify(
///     address: &str,
///     account_name: &str,
///     path: &str,
/// ) -> trezor_app_sdk::Result<()> {
///     modui::verify_address("address", address, Some(account_name), Some(path))
/// }
/// ```
pub fn verify_address(
    step: &str,
    address: &str,
    account: Option<&str>,
    path: Option<&str>,
) -> Result<()> {
    yes_or_no(call(TrezorUiEnum::VerifyAddress(VerifyRequest {
        step: step.into(),
        value: address.into(),
        account: account.into(),
        path: path.into(),
    })))
}

/// Shows the person a public key of theirs to check against the host, and waits
/// for the answer.
///
/// The same as [`verify_address`] for a key. A title alone cannot turn an
/// address screen into a key screen: a key goes out with its own
/// ButtonRequest type and is not split into chunks, as core's own `show_pubkey`
/// does it.
///
/// - `step` — the step name, relative to the app, such as `"pubkey"`; see
///   [step names](crate::modui#step-names).
/// - `pubkey` — the public key, as the host will show it.
/// - `account` — the account's name, such as `"TRX #1"`.
/// - `path` — the derivation path.
///
/// `Ok(())`: it matches. `Err(`[`crate::Error::Cancelled`]`)`: it does not, or
/// the person refused.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui;
///
/// fn verify(
///     xpub: &str,
///     account_name: &str,
///     path: &str,
/// ) -> trezor_app_sdk::Result<()> {
///     modui::verify_pubkey("pubkey", xpub, Some(account_name), Some(path))
/// }
/// ```
pub fn verify_pubkey(
    step: &str,
    pubkey: &str,
    account: Option<&str>,
    path: Option<&str>,
) -> Result<()> {
    yes_or_no(call(TrezorUiEnum::VerifyPubkey(VerifyRequest {
        step: step.into(),
        value: pubkey.into(),
        account: account.into(),
        path: path.into(),
    })))
}
