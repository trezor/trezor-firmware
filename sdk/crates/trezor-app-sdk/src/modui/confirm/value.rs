//! Confirming a single value. The public docs live on [`value`].

use crate::app_runtime2::get_ui_or_die;
use crate::modui::internal::answer;
use crate::modui::{Commitment, ExtraItem};
use crate::structs::ConfirmValue;
pub use crate::structs::ValueKind;
use crate::traits::ui::UiV1Dyn as _;
use crate::{IntoAppResult, Result};

/// A note along the bottom of the screen.
///
/// Two variants rather than a string plus a flag, so the caller names what the
/// note means and the library picks how loud it looks.
#[derive(Copy, Clone)]
pub enum Footer<'a> {
    /// Ordinary guidance.
    Hint(&'a str),
    /// Something the person should weigh before confirming.
    Warning(&'a str),
}

/// Asks the person to confirm one value, and waits for the answer.
///
/// - `title` — the screen's heading, such as `"Send"`.
/// - `value` — the value itself, shown verbatim.
/// - `kind` — what the value is, which decides how it is formatted.
/// - `subtitle` — optional line under the heading, such as `"Recipient"`.
/// - `description` — optional text above the value.
/// - `footer` — optional note along the bottom of the screen.
/// - `commitment` — whether confirming this is the person's final yes; see
///   [`Commitment`].
/// - `br` — the step name the host sees; see
///   [step names](crate::modui#step-names).
/// - `extras` — more the person can look at from this screen; see
///   [extras](crate::modui#extras-and-the-way-out).
///
/// The person can always refuse, so the block takes no `cancel`: the way out
/// is on the screen, or in its menu where the menu button takes its place.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{Commitment, confirm};
///
/// fn confirm_recipient(address: &str) -> trezor_app_sdk::Result<()> {
///     confirm::value(
///         "Send",
///         address,
///         confirm::ValueKind::Address,
///         Some("Recipient"),
///         None,
///         Some(confirm::Footer::Hint("Check with the source.")),
///         Commitment::Step,
///         "app/send/recipient",
///         &[],
///     )
/// }
/// ```
#[allow(clippy::too_many_arguments)]
pub fn value(
    title: &str,
    value: &str,
    kind: ValueKind,
    subtitle: Option<&str>,
    description: Option<&str>,
    footer: Option<Footer<'_>>,
    commitment: Commitment,
    br: &str,
    extras: &[ExtraItem<'_>],
) -> Result<()> {
    let (footer, footer_warning) = match footer {
        None => (None, false),
        Some(Footer::Hint(text)) => (Some(text), false),
        Some(Footer::Warning(text)) => (Some(text), true),
    };
    let request = ConfirmValue {
        title: title.into(),
        value: value.into(),
        kind,
        subtitle: subtitle.into(),
        description: description.into(),
        footer: footer.into(),
        footer_warning,
        commitment,
        br_name: br.into(),
        extras: extras.into(),
    };
    answer(get_ui_or_die().confirm_value(request).into_app_result()?)
}
