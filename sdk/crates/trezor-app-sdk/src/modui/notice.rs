//! Telling the person something. The public docs live on [`show`].
//!
//! One block for every callout, one contract across models: the same request
//! answers the same way everywhere. Failures are not among the callouts; see
//! [`Severity`].
//!
//! WIP: extras have a menu only on delizia (info, warning) and eckhart (info).
//!
//! WIP: `Done` waits for a tap on bolt and caesar.
//!
//! WIP: `cancel` ignored — every layout takes `_cancel`. Today the screen
//! decides: danger always; warning on bolt/eckhart (caesar/delizia
//! `show_warning` drop `allow_cancel`), delizia also with extras; info only
//! with extras (delizia/eckhart, menu Cancel); success/done never.
//! Direction: way out moves to the menu, like confirmations. `cancel` =
//! "menu button even without extras"; `extapp_menu` adds Cancel. Info and
//! warning only. Bolt: no menus, keeps on-screen X. Caesar: waits on #7694.

use crate::Result;
use crate::modui::ExtraItem;
use crate::modui::internal::{BR_CODE_OTHER, answer, call};
pub use crate::traits::ui::Severity;
use crate::traits::ui::ShowNotice as WireShowNotice;

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`show`], built by [`Notice::new`].
pub struct Notice<'a> {
    severity: Severity,
    title: &'a str,
    content: &'a str,
    br: &'a str,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> Notice<'a> {
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
    ///   Not every severity can show them; see [`show`].
    /// - `cancel` — whether the person must be able to back out of it. How
    ///   they do is the model's. WIP: ignored today; see the module notes.
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
/// The contract is uniform across models: the same request answers the same
/// way everywhere. How each model renders a severity is its own business, and
/// may look entirely different — but which replies can arrive is not:
///
/// - Moving on is `Ok(())`, the ordinary case.
/// - Backing out is `Err(`[`crate::Error::Cancelled`]`)`, and only a notice
///   that offers a way out can answer it: with `cancel` set, every model
///   offers one; without, a model may still (a danger screen always does).
///   WIP: not yet; see the module notes.
/// - [`Severity::Done`] answers `Ok(())` without waiting for the person:
///   it is the last screen of the flow, nothing on the device follows it, and
///   the host's response should not wait on a dismissal. The screen may stay
///   up for a moment or until the person acknowledges it, whichever the model
///   does — the call has already returned. WIP: not on bolt and caesar.
///
/// There is no error notice: an app that fails returns `Err`, and whether the
/// person sees a screen for that is core's decision.
///
/// # Errors
///
/// Extras work only where the model's screen for that severity has a menu.
/// Elsewhere the notice is drawn without them and the model says so, rather
/// than fail. Otherwise see
/// [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::notice;
///
/// fn warn_unknown_contract() -> trezor_app_sdk::Result<()> {
///     notice::show(notice::Notice::new(
///         notice::Severity::Danger,
///         "Important",
///         "Unknown contract address.",
///         "app/unknown_contract",
///         &[],
///         true,
///     ))
/// }
///
/// fn signed() -> trezor_app_sdk::Result<()> {
///     // The last screen of the flow; it offers no way back out.
///     notice::show(notice::Notice::new(
///         notice::Severity::Done,
///         "Done",
///         "Transaction signed",
///         "app/signed",
///         &[],
///         false,
///     ))?;
///     Ok(())
/// }
/// ```
pub fn show(params: Notice<'_>) -> Result<()> {
    let request = WireShowNotice::new(
        params.severity,
        params.title,
        params.content,
        !params.extras.is_empty(), // external_menu: how the extras are reached
        params.cancel,             // cancel: the model provides the way out
        Some(params.br),           // br_name: the step's name; the app owns it
        BR_CODE_OTHER,             // see the constant
    );

    answer(call(&request, params.extras, Some(params.br))?)
}
