//! Confirming an opaque byte blob. The public docs live on [`data`].
//!
//! This block exists because of *what* it shows — raw bytes with no meaning
//! the device can interpret, rendered as hex — and not because of how much of
//! it there is. Length is not the caller's problem: a blob of any size is one
//! call returning one outcome. The firmware sends it to core in chunks.

use crate::app_runtime::{get_ui_or_die, system_exit_fatal};
use crate::modui::ExtraItem;
use crate::structs::{ConfirmData, TrezorUiResult};
use crate::traits::ui::UiV1Dyn as _;
use crate::{Error, Result};

/// Asks the person to confirm raw bytes, and waits for the answer.
///
/// - `title` — the heading of every screen.
/// - `data` — the bytes, of any length.
/// - `subtitle` — optional line under the heading.
/// - `br` — the step name the host sees; see
///   [step names](crate::modui#step-names).
/// - `extras` — more the person can look at from this screen; see
///   [extras](crate::modui#extras-and-the-way-out).
///
/// For data the device cannot interpret, such as contract call data. The
/// bytes are shown as hex, a screen at a time, and a blob of any length is
/// still one call with one outcome: the app never sees how it was split.
///
/// `Ok` means the person went through all of it: there is no way to
/// accept the rest unread.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::confirm;
///
/// fn confirm_calldata(calldata: &[u8]) -> trezor_app_sdk::Result<()> {
///     confirm::data("Transaction data", calldata, None, "app/data", &[])
/// }
/// ```
pub fn data(
    title: &str,
    data: &[u8],
    subtitle: Option<&str>,
    br: &str,
    extras: &[ExtraItem<'_>],
) -> Result<()> {
    let request = ConfirmData {
        title: title.into(),
        data: data.into(),
        subtitle: subtitle.into(),
        br_name: br.into(),
        extras: extras.into(),
    };
    match get_ui_or_die().confirm_data(request).into_result() {
        Ok(TrezorUiResult::Confirmed | TrezorUiResult::ConfirmedAll) => Ok(()),
        Ok(TrezorUiResult::Cancelled) => Err(Error::Cancelled),
        Ok(_) => system_exit_fatal("unexpected UI reply", file!(), line!()),
        Err(e) => system_exit_fatal(e.message(), file!(), line!()),
    }
}
