//! Telling the person that work is happening. The public docs live on
//! [`progress`] and [`Progress`].
//!
//! Not a layout: nothing is asked, nothing is answered, and the calls do not
//! wait for the person. The app never ends a progress by hand: dropping the
//! [`Progress`] ends it, so a lost end cannot leave a bar up for work that
//! stopped. Core keeps the count and turns it into the bar.

use crate::app_runtime::get_ui_or_die;
use crate::traits::ui::UiV1Dyn as _;
use crate::{IntoAppResult, Result};

/// A progress that is running. Dismissing it is not the app's to do: it goes
/// away when this value is dropped, whatever happened to the work.
///
/// Handed to the work by [`progress`].
pub struct Progress(());

/// Runs `work` under a progress of the given label, and returns what it
/// returns, or the error that kept the progress from starting.
///
/// The progress appears before `work` runs and disappears after — on success, on
/// error, on an early return through `?`, all the same, because its lifetime is
/// the call.
///
/// - `label` — text shown with the bar, such as `"Signing"`.
/// - `total` — how much work there is, in the app's own unit. `None` shows
///   motion without a fill, and steps do nothing.
/// - `work` — the work, given the [`Progress`] handle to report steps with.
///
/// One progress at a time: starting one inside another's `work` ends the app.
/// A screen the app asks for while a progress runs covers the bar, which comes
/// back once the person has answered. A progress that cannot be started is an
/// error and `work` does not run: `Err(Error::Stopped)` when core asked the app
/// to stop, `Err(Error::ServiceError)` when the start could not reach core.
///
/// # Example
///
/// Counted work, with the label changing per step:
///
/// ```no_run
/// use trezor_app_sdk::Result;
/// use trezor_app_sdk::modui::progress;
///
/// fn sign(inputs: &[u8]) -> Result<Vec<u8>> {
///     progress("Signing", Some(inputs.len() as u32), |p| {
///         inputs
///             .iter()
///             .enumerate()
///             .map(|(i, input)| {
///                 p.label(&format!("Signing input {}/{}", i + 1, inputs.len()));
///                 let sig = *input;
///                 p.step(1);
///                 sig
///             })
///             .collect()
///     })
/// }
/// ```
///
/// Work the app cannot count:
///
/// ```no_run
/// use trezor_app_sdk::Result;
/// use trezor_app_sdk::modui::progress;
///
/// fn derive_key(seed: &[u8]) -> Result<u32> {
///     progress("Deriving key", None, |_| seed.len() as u32)
/// }
/// ```
pub fn progress<T>(
    label: &str,
    total: Option<u32>,
    work: impl FnOnce(&mut Progress) -> T,
) -> Result<T> {
    // A `Progress` exists only once core has accepted the start, so dropping
    // it always ends a progress that is running.
    get_ui_or_die()
        .init_progress(label.into(), total.unwrap_or(0))
        .into_app_result()?;
    Ok(work(&mut Progress(())))
}

impl Progress {
    /// Reports that `units` of work are done, of the total given at the start.
    ///
    /// Deliberately infallible: an update is a status note, not a step of the
    /// work, and a status note that cannot be delivered must not abort the work
    /// it describes. The person at worst sees a stale bar until the next update
    /// or the end.
    ///
    /// Past the total the bar pins full rather than wrapping; with no total
    /// given there is no fill to grow, and this does nothing.
    pub fn step(&mut self, units: u32) {
        let _ = get_ui_or_die().step_progress(units);
    }

    /// Changes the text under the bar while the work goes on, such as between
    /// phases.
    ///
    /// Deliberately infallible, for the same reason as [`step`](Progress::step):
    /// the person at worst sees a stale label until the next one.
    pub fn label(&mut self, text: &str) {
        let _ = get_ui_or_die().label_progress(text.into());
    }
}

impl Drop for Progress {
    fn drop(&mut self) {
        // Nothing useful can be done if this fails, and a panic here would
        // replace whatever error is already unwinding out.
        let _ = get_ui_or_die().end_progress();
    }
}
