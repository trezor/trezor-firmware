//! Confirming a list of key/value facts. The public docs live on
//! [`properties`].

use crate::modui::internal::{answer, call};
use crate::modui::{Commitment, ExtraItem};
use crate::structs::{ConfirmProperties, Property};
use crate::{Error, Result};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`properties`], built by [`Properties::new`].
pub struct Properties<'a> {
    /// The request as core reads it; it goes through the FFI as is.
    request: ConfirmProperties<'a>,
    /// Shown by the library from the screen's menu; never sent.
    extras: &'a [ExtraItem<'a>],
}

impl<'a> Properties<'a> {
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
            request: ConfirmProperties {
                title: title.into(),
                props: props.into(),
                subtitle: subtitle.into(),
                commitment,
                br_name: br.into(),
            },
            extras,
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
/// This block cannot show extras yet: a non-empty `extras` is refused with
/// [`crate::Error::ValueError`]. Otherwise see
/// [errors](crate::modui#errors).
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
    // This block's wire has no menu button yet, so anything behind one would
    // be silently unreachable. Refusing is worse to use and better to debug.
    if !params.extras.is_empty() {
        return Err(Error::ValueError("extras not yet supported by this block"));
    }
    let br = params.request.br_name.as_str();
    answer(call(&params.request, params.extras, Some(br))?)
}
