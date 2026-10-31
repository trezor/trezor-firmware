//! The end of the flow. The public docs live on [`done`].

use crate::modui::call::call;
use crate::structs::{DoneRequest, TrezorUiEnum};

/// Tells the person the flow is finished, such as "Transaction signed".
///
/// Returns at once; the screen goes away by itself after a timeout on every
/// model. It takes a step name, so hosts and tests can see it.
///
/// - `step` — the step name, relative to the app, such as `"signed"`; see
///   [step names](crate::modui#step-names).
/// - `text` — what the screen says.
///
/// The answer is ignored: there is nothing left for the app to do with it. WIP:
/// bolt and caesar wait for a tap today instead of going away by themselves.
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui;
///
/// fn sign() -> trezor_app_sdk::Result<u8> {
///     let signature = 0u8;
///     modui::done("signed", "Transaction signed");
///     Ok(signature)
/// }
/// ```
pub fn done(step: &str, text: &str) {
    let request = DoneRequest {
        step: step.into(),
        text: text.into(),
    };
    let _ = call(TrezorUiEnum::Done(request));
}
