//! Progress: telling the person that work is happening.
//!
//! Not a layout. A layout asks the person a question and waits; progress is the
//! opposite — the app is working, and the person should see that it has not
//! stalled. Nothing is ever confirmed, nothing is answered, and the calls do not
//! wait for the person.
//!
//! # Ownership
//!
//! The app never ends a progress by hand. It appears when a progress starts and
//! disappears when the work is done — whether the work finished, failed, or
//! returned early through `?`. A lost `End` would leave the person staring at a
//! bar for work that stopped, which is precisely what a scope is for.
//!
//! # Form
//!
//! The work is one closure, and it is handed the [`Progress`] to report steps
//! with. There is no second entry point: a progress that the app cannot write as
//! one closure has no form here. WIP: work driven from the host's message loop,
//! as ethereum's blind signing is, needs a handle form; see the open questions
//! in the reference.
//!
//! Work with no intermediate steps to report — one long operation, or waiting on
//! the host:
//!
//! ```text
//! let key = progress("Deriving key", None, |_| derive());
//! ```
//!
//! Work in steps, each reported; the total is declared once, in whatever unit the
//! app counts, and the percent is never the app's arithmetic:
//!
//! ```text
//! let digest = progress("Signing", Some(data.len() as u32), |prog| {
//!     let mut hasher = Hasher::new();
//!     for chunk in data.chunks(1024) {
//!         hasher.update(chunk);
//!         prog.step(chunk.len() as u32);
//!     }
//!     hasher.finalize()
//! });
//! ```
//!
//! # Example
//!
//! ```text
//! let signatures = progress("Signing", Some(inputs.len() as u32), |prog| {
//!     inputs.iter().enumerate().map(|(i, input)| {
//!         prog.label(&format!("Signing input {}/{}", i + 1, inputs.len()));
//!         let sig = sign_input(input);
//!         prog.step(1);
//!         sig
//!     }).collect::<Vec<_>>()
//! });
//! ```

use crate::app_runtime::{get_ui_or_die, system_exit_fatal};
use crate::traits::ui::UiV1Dyn as _;

// ============================================================================
// Data types
// ============================================================================

/// A progress that is running. Dismissing it is not the app's to do: it goes
/// away when this value is dropped, whatever happened to the work.
///
/// Handed to the work by [`progress`]; see the module docs.
pub struct Progress {
    // Built only once core has accepted the start, so dropping it always
    // ends a progress that is running. Core keeps the count.
    _running: (),
}

// ============================================================================
// Entry point
// ============================================================================

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
/// A progress that cannot be shown ends the app; see [`Progress`].
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
    let mut guard = Progress::start(label, total.unwrap_or(0));
    work(&mut guard)
}

impl Progress {
    /// Starts a progress and returns it, running. Dropping the value ends it.
    ///
    /// If the request cannot reach core, the app ends; this never returns
    /// without a running progress.
    fn start(label: &str, total: u32) -> Self {
        if let Err(e) = get_ui_or_die()
            .init_progress(label.into(), total)
            .into_result()
        {
            system_exit_fatal(e.message(), file!(), line!());
        }
        Self { _running: () }
    }

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
