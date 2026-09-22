//! Telling the person something. The public docs live on [`show_notice`].
//!
//! One block for every callout, where there used to be a function per kind.
//! Failures are not among them; see [`Severity`].

use super::extra::ExtraItem;
use super::{BR_CODE_OTHER, UiOutcome, call};
use crate::Result;
pub use crate::structs::Severity;
use crate::structs::{ShowNotice as WireShowNotice, TrezorUiEnum};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`show_notice`], built by [`ShowNotice::new`].
pub struct ShowNotice<'a> {
    severity: Severity,
    title: &'a str,
    content: &'a str,
    br: &'a str,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> ShowNotice<'a> {
    /// A notice of the given severity.
    ///
    /// - `severity` — what kind of news this is; see [`Severity`].
    /// - `title` — the notice's heading. Some models have a fixed heading for
    ///   some severities and do not show it.
    /// - `content` — what the notice says.
    /// - `br` — the step name the host sees; see
    ///   [step names](crate::modui#step-names).
    /// - `extras` — more the person can look at from this screen; see
    ///   [extras](crate::modui#extras-and-the-way-out).
    ///   Not every severity can show them; see [`show_notice`].
    /// - `cancel` — whether the extras also offer a way to abandon the block.
    pub fn new(
        severity: Severity,
        title: &'a str,
        content: &'a str,
        br: &'a str,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            severity,
            title,
            content,
            br,
            extras,
            cancel,
        }
    }

    /// Whether the screen has anything to offer besides its main content.
    fn offers_more(&self) -> bool {
        !self.extras.is_empty() || self.cancel
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Tells the person something, and waits for them to move on.
///
/// The severity decides everything about how it looks: its screen, its button
/// words, and whether it goes away by itself. The same severity looks the same
/// from every app.
///
/// A [`Severity::Danger`] notice can always be refused, and a
/// [`Severity::Warning`] can on most models; call [`UiOutcome::confirmed`] on
/// both. The other severities only ever answer `Confirmed`, which apps usually
/// ignore.
///
/// There is no error notice: an app that fails returns `Err`, and whether the
/// person sees a screen for that is core's decision.
///
/// # Errors
///
/// Extras, or `cancel: true`, work only where the model's screen for that
/// severity has a menu — today [`Severity::Info`], and not on every model.
/// Elsewhere core ends the app's session rather than answer. Otherwise see
/// [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{self as ui, Severity, ShowNotice};
///
/// fn warn_unknown_contract() -> trezor_app_sdk::Result<()> {
///     ui::show_notice(ShowNotice::new(
///         Severity::Danger,
///         "Important",
///         "Unknown contract address.",
///         "app/unknown_contract",
///         &[],
///         false,
///     ))?
///     .confirmed()
/// }
///
/// fn signed() -> trezor_app_sdk::Result<()> {
///     // The last screen of the flow: nothing hangs on how it went away.
///     let _ = ui::show_notice(ShowNotice::new(
///         Severity::Done,
///         "Done",
///         "Transaction signed",
///         "app/signed",
///         &[],
///         false,
///     ))?;
///     Ok(())
/// }
/// ```
pub fn show_notice(params: ShowNotice<'_>) -> Result<UiOutcome> {
    let request = WireShowNotice::new(
        params.severity,
        params.title,
        params.content,
        params.offers_more(), // external_menu: how the extras are reached
        Some(params.br),      // br_name: the step's name; the app owns it
        BR_CODE_OTHER,        // legacy field; see the constant
    );

    call(
        &TrezorUiEnum::ShowNotice(request),
        params.extras,
        params.cancel,
        Some(params.br),
    )
}
