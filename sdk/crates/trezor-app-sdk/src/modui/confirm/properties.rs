//! Confirming a list of key/value facts. The public docs live on
//! [`properties`].

use crate::app_runtime2::{get_ui_or_die, system_exit_fatal};
use crate::modui::{Commitment, ExtraItem};
use crate::structs::{ConfirmProperties, Property, TrezorUiEnum, TrezorUiResult};
use crate::traits::ui::UiV1Dyn as _;
use crate::{Error, Result};

/// Asks the person to confirm a list of facts, and waits for the answer.
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
///     confirm::properties("Summary", &props, None, Commitment::Step, "app/stake", &[])
/// }
/// ```
pub fn properties(
    title: &str,
    props: &[Property<'_>],
    subtitle: Option<&str>,
    commitment: Commitment,
    br: &str,
    extras: &[ExtraItem<'_>],
) -> Result<()> {
    let request = ConfirmProperties {
        title: title.into(),
        props: props.into(),
        subtitle: subtitle.into(),
        commitment,
        br_name: br.into(),
        extras: extras.into(),
    };
    match get_ui_or_die()
        .ui_call(TrezorUiEnum::ConfirmProperties(request))
        .into_result()
    {
        Ok(TrezorUiResult::Confirmed) => Ok(()),
        Ok(TrezorUiResult::Cancelled) => Err(Error::Cancelled),
        Ok(_) => system_exit_fatal("unexpected UI reply", file!(), line!()),
        Err(e) => system_exit_fatal(e.message(), file!(), line!()),
    }
}
