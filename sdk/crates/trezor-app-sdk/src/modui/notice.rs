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

use crate::app_runtime2::{get_ui_or_die, system_exit_fatal};
use crate::modui::ExtraItem;
pub use crate::structs::Severity;
use crate::structs::{ShowNotice, TrezorUiEnum, TrezorUiResult};
use crate::traits::ui::UiV1Dyn as _;
use crate::{Error, Result};

/// Tells the person something, and waits for them to move on.
///
/// - `severity` — what kind of news this is; see [`Severity`].
/// - `title` — the notice's heading. Some models have a fixed heading for
///   some severities and do not show it.
/// - `content` — what the notice says.
/// - `cancel` — whether the person must be able to back out of it. How
///   they do is the model's. WIP: ignored today; see the module notes.
/// - `br` — the step name the host sees; see
///   [step names](crate::modui#step-names).
/// - `extras` — more the person can look at from this screen; see
///   [extras](crate::modui#extras-and-the-way-out).
///   Not every severity can show them; see below.
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
///     notice::show(
///         notice::Severity::Danger,
///         "Important",
///         "Unknown contract address.",
///         true,
///         "app/unknown_contract",
///         &[],
///     )
/// }
///
/// fn signed() -> trezor_app_sdk::Result<()> {
///     // The last screen of the flow; it offers no way back out.
///     notice::show(
///         notice::Severity::Done,
///         "Done",
///         "Transaction signed",
///         false,
///         "app/signed",
///         &[],
///     )?;
///     Ok(())
/// }
/// ```
pub fn show(
    severity: Severity,
    title: &str,
    content: &str,
    cancel: bool,
    br: &str,
    extras: &[ExtraItem<'_>],
) -> Result<()> {
    let request = ShowNotice {
        severity,
        title: title.into(),
        content: content.into(),
        cancel,
        br_name: br.into(),
        extras: extras.into(),
    };
    match get_ui_or_die()
        .ui_call(TrezorUiEnum::ShowNotice(request))
        .into_result()
    {
        Ok(TrezorUiResult::Confirmed) => Ok(()),
        Ok(TrezorUiResult::Cancelled) => Err(Error::Cancelled),
        Ok(_) => system_exit_fatal("unexpected UI reply", file!(), line!()),
        Err(e) => system_exit_fatal(e.message(), file!(), line!()),
    }
}
