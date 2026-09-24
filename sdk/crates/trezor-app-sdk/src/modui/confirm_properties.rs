//! Confirming a list of key/value facts. The public docs live on
//! [`confirm_properties`].

use super::extra::ExtraItem;
use super::{BR_CODE_OTHER, Commitment, UiOutcome, call};
use crate::structs::{ConfirmProperties as WireConfirmProperties, Property, TrezorUiEnum};
use crate::{Error, Result};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`confirm_properties`], built by [`ConfirmProperties::new`].
pub struct ConfirmProperties<'a> {
    title: &'a str,
    props: &'a [Property<'a>],
    subtitle: Option<&'a str>,
    commitment: Commitment,
    br: &'a str,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

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
    ///   Not shown by this block yet; see [`confirm_properties`].
    /// - `cancel` — whether the extras also offer a way to abandon the block.
    pub fn new(
        title: &'a str,
        props: &'a [Property<'a>],
        subtitle: Option<&'a str>,
        commitment: Commitment,
        br: &'a str,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            title,
            props,
            subtitle,
            commitment,
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

/// Asks the person to confirm a list of facts, and waits for the answer.
///
/// # Errors
///
/// This block cannot show extras yet: a non-empty `extras` is refused with
/// [`crate::Error::ValueError`], and `cancel` has no effect. Otherwise see
/// [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{self as ui, Commitment, ConfirmProperties, Property};
///
/// fn confirm_stake(amount: &str) -> trezor_app_sdk::Result<()> {
///     let props = [
///         Property::plain("Amount", amount),
///         Property::plain("Resource", "Energy"),
///     ];
///     ui::confirm_properties(ConfirmProperties::new("Summary", &props, None, Commitment::Step, "app/stake", &[], true))?
///         .confirmed()
/// }
/// ```
pub fn confirm_properties(params: ConfirmProperties<'_>) -> Result<UiOutcome> {
    // This block's wire has no menu button yet, so anything behind one would
    // be silently unreachable. Refusing is worse to use and better to debug.
    if !params.extras.is_empty() {
        return Err(Error::ValueError("extras not yet supported by this block"));
    }
    let request = WireConfirmProperties::new(
        params.title,
        params.props,
        params.subtitle,
        None, // verb: the label follows the gesture, which the block owns
        params.commitment == Commitment::Final, // hold: follows from the commitment
        Some(params.br), // br_name: the step's name; the app owns it (see the field docs)
        BR_CODE_OTHER, // legacy field; see the constant
    );

    call(
        &TrezorUiEnum::ConfirmProperties(request),
        params.extras,
        params.cancel,
        Some(params.br),
    )
}
