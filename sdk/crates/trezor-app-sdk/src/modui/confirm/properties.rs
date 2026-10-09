//! Confirming a list of key/value facts. The public docs live on
//! [`properties`].

use crate::app_runtime2::get_ui_or_die;
use crate::modui::internal::answer;
use crate::modui::{Commitment, ExtraItem};
use crate::structs::{ConfirmProperties, Property};
use crate::traits::ui::UiV1Dyn as _;
use crate::{IntoAppResult, Result};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`properties`], built by [`Properties::new`].
pub type Properties<'a> = ConfirmProperties<'a>;

impl<'a> ConfirmProperties<'a> {
    /// Confirms the facts in `props` under `title`.
    ///
    /// - `title` — the screen's heading.
    /// - `props` — the facts, in the order they are shown.
    /// - `subtitle` — optional line under the heading.
    /// - `commitment` — whether confirming this is the person's final yes; see
    ///   [`Commitment`].
    /// - `br` — the step name the host sees; see
    ///   [step names](crate::modui#step-names).
    /// - `extras` — more the person can look at from this screen; see
    ///   [extras](crate::modui#extras-and-the-way-out).
    ///   Not shown by this block yet; see [`properties`].
    pub fn new(
        title: &'a str,
        props: &'a [Property<'a>],
        subtitle: Option<&'a str>,
        commitment: Commitment,
        br: &'a str,
        extras: &'a [ExtraItem<'a>],
    ) -> Self {
        Self {
            title: title.into(),
            props: props.into(),
            subtitle: subtitle.into(),
            commitment,
            br_name: br.into(),
            extras: extras.into(),
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Asks the person to confirm a list of facts, and waits for the answer.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{Commitment, Property, confirm};
///
/// fn confirm_stake(amount: &str) -> trezor_app_sdk::Result<()> {
///     let props = [
///         Property::plain("Amount", amount),
///         Property::plain("Resource", "Energy"),
///     ];
///     confirm::properties(confirm::Properties::new("Summary", &props, None, Commitment::Step, "app/stake", &[]))
/// }
/// ```
pub fn properties(params: Properties<'_>) -> Result<()> {
    answer(
        get_ui_or_die()
            .confirm_properties(params)
            .into_app_result()?,
    )
}
