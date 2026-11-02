//! Telling the person that work is happening. The public docs live on
//! [`progress`] and [`Progress`].
//!
//! Not a layout: nothing is asked, nothing is answered, and the calls do not
//! wait for the person. The app never ends a progress by hand: dropping the
//! [`Progress`] ends it, so a lost end cannot leave a bar up for work that
//! stopped. Core keeps the count and turns it into the bar.

use crate::app_runtime::{get_ui_or_die, system_exit, system_exit_fatal};
use crate::traits::ui::UiV1Dyn as _;
use crate::traits::wire::WireError;

/// A progress that is running. Dismissing it is not the app's to do: it goes
/// away when this value is dropped, whatever happened to the work.
///
/// Handed to the work by [`progress`].
pub struct Progress {
    // Built only once core has accepted the start, so dropping it always
    // ends a progress that is running. Core keeps the count.
    _running: (),
}

/// Runs `work` under a progress of the given label, and returns what it
/// returns.
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
/// back once the person has answered. A progress that cannot be shown ends the
/// app.
///
/// # Example
///
/// Counted work, with the label changing per step:
///
/// ```no_run
/// use trezor_app_sdk::modui::progress;
///
/// fn sign(inputs: &[u8]) -> Vec<u8> {
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
/// use trezor_app_sdk::modui::progress;
///
/// fn derive_key(seed: &[u8]) -> u32 {
///     progress("Deriving key", None, |_| seed.len() as u32)
/// }
/// ```
pub fn progress<T>(label: &str, total: Option<u32>, work: impl FnOnce(&mut Progress) -> T) -> T {
    // If the start cannot reach core, the app ends, so a `Progress` only ever
    // exists while one is running, and dropping it always ends that one.
    match get_ui_or_die()
        .init_progress(label.into(), total.unwrap_or(0))
        .into_result()
    {
        Ok(()) => {}
        // Core asked the app to stop. There is no error to hand back from
        // here, so the app exits now, cleanly, as its entry point would.
        Err(WireError::Stopped) => system_exit(),
        Err(e) => system_exit_fatal(e.message(), file!(), line!()),
    }
    let mut running = Progress { _running: () };
    work(&mut running)
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

    /// Changes the text under the bar while the work goes on, as Monero does
    /// today between phases.
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
