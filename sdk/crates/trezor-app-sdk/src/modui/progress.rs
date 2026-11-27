//! Telling the person that work is happening. The public docs live on
//! [`progress`] and [`Progress`].
//!
//! Not a layout: nothing is asked, nothing is answered, and the calls do not
//! wait for the person. Every call sends the whole state of the bar — its
//! label, how much is done and of how much — so there is nothing to start or
//! end: the bar stays until the next screen takes its place.

use crate::app_runtime::get_ui_or_die;
use crate::traits::ui::{ProgressV1, UiV1Dyn as _};
use crate::{IntoAppResult, Result};

/// Shows a progress bar: `done` of `total`, under `label`.
///
/// - `label` — what the work is, such as `"Signing"`.
/// - `done` — how much of it is done, in the app's own unit. Past `total` the
///   bar shows full.
/// - `total` — how much work there is, in the same unit. `0` shows motion
///   without a fill.
///
/// Each call describes the bar completely; nothing from an earlier call
/// carries over. For counted work in steps, [`Progress`] keeps the count.
///
/// A screen the app asks for while the bar is up covers it, and the bar comes
/// back once the person has answered. `Err(Error::Stopped)` when core asked the
/// app to stop, `Err(Error::ServiceError)` when the call could not reach core.
///
/// # Example
///
/// Work the app cannot count:
///
/// ```no_run
/// use trezor_app_sdk::Result;
/// use trezor_app_sdk::modui::progress;
///
/// fn derive_key(seed: &[u8]) -> Result<u32> {
///     progress("Deriving key", 0, 0)?;
///     Ok(seed.len() as u32)
/// }
/// ```
pub fn progress(label: &str, done: u32, total: u32) -> Result<()> {
    get_ui_or_die()
        .progress_v1(ProgressV1 {
            label: label.into(),
            done,
            total,
        })
        .into_app_result()
}

/// A progress bar for one piece of counted work: it keeps the label, the count
/// and the total, and every method sends them all with [`progress`].
///
/// A plain local value: the next piece of work makes its own, and inherits
/// nothing from this one. Dropping it changes nothing on the screen.
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::Result;
/// use trezor_app_sdk::modui::Progress;
///
/// fn sign(inputs: &[u8]) -> Result<Vec<u8>> {
///     let mut p = Progress::new("Signing", inputs.len() as u32)?;
///     let mut signatures = Vec::new();
///     for input in inputs {
///         signatures.push(*input);
///         p.step(1)?;
///     }
///     p.label("Finalizing")?;
///     Ok(signatures)
/// }
/// ```
pub struct Progress<'a> {
    label: &'a str,
    done: u32,
    total: u32,
}

impl<'a> Progress<'a> {
    /// Shows the bar with nothing done yet. `total` as in [`progress`].
    pub fn new(label: &'a str, total: u32) -> Result<Self> {
        let bar = Self {
            label,
            done: 0,
            total,
        };
        bar.show()?;
        Ok(bar)
    }

    /// Counts `units` more of the work as done.
    pub fn step(&mut self, units: u32) -> Result<()> {
        self.done = self.done.saturating_add(units);
        self.show()
    }

    /// Sets how much of the work is done.
    pub fn set(&mut self, done: u32) -> Result<()> {
        self.done = done;
        self.show()
    }

    /// Changes what the work is called, such as between phases.
    pub fn label(&mut self, label: &'a str) -> Result<()> {
        self.label = label;
        self.show()
    }

    fn show(&self) -> Result<()> {
        progress(self.label, self.done, self.total)
    }
}
