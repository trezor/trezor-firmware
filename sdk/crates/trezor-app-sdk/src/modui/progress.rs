//! Progress: telling the person that work is happening.
//!
//! Not a block. A block asks the person a question and waits; progress is the
//! opposite — the app is working, and the person should see that it has not
//! stalled. Nothing is ever confirmed, nothing is answered, and the calls do
//! not wait for the person.
//!
//! # Ownership
//!
//! The app never ends a progress by hand. It appears when a progress starts
//! and disappears when the work is done — whether the work finished, failed,
//! or returned early through `?`. A lost `End` would leave the person staring
//! at a bar for work that stopped, which is precisely what a scope is for;
//! the same reasoning that closes a [`LayoutHandle`](super::layout::LayoutHandle) on drop.
//!
//! # Forms
//!
//! Three entry points, one rule of choice: if the work can be written as one
//! closure, use a closure; if it cannot, take the handle and keep it bound
//! until the work is done.
//!
//! Work with no intermediate steps to report — one long operation, or waiting
//! on the host:
//!
//! ```text
//! let key = ui::progress("Deriving key", Total::Unknown, || derive())?;
//! ```
//!
//! Work in steps, each reported; the total is declared once, in whatever unit
//! the app counts, and the percent is never the app's arithmetic:
//!
//! ```text
//! let digest = ui::progress_with("Signing", Total::Units(data.len() as u32), |prog| {
//!     let mut hasher = Hasher::new();
//!     for chunk in data.chunks(1024) {
//!         hasher.update(chunk);
//!         prog.step(chunk.len() as u32);
//!     }
//!     hasher.finalize()
//! })?;
//! ```
//!
//! Work a closure cannot span — phases spread across calls, a handle held in a
//! struct. There is no `finish` to call: dropping the value *is* finishing,
//! so it must stay bound for as long as the work runs, and scope exit ends
//! it however the function left — `Ok`, `Err`, or `?` in between:
//!
//! ```text
//! let mut prog = ui::Progress::start("Signing", Total::Units(2))?;
//! let digest = hash(tx)?;                    // early exit: prog drops, bar ends
//! prog.step(1);
//! confirm_the_person()?;                     // refusal: same
//! let sig = sign(&digest);
//! prog.step(1);
//! Ok(sig)                                    // scope exit: prog drops, bar ends
//! ```
//!
//! The trap of this form, stated plainly: `let _ = Progress::start(..)`
//! drops the value at the end of that statement, ending the progress before
//! any work runs. Bind it to a name and let the scope do the rest.
//!
//! # Example
//!
//! ```text
//! let done = ui::progress_with("Signing", Total::Units(data.len() as u32), |prog| {
//!     let mut done = 0;
//!     for chunk in data.chunks(1024) {
//!         done += hash_all(chunk);
//!         prog.step(chunk.len() as u32);
//!     }
//!     done
//! })?;
//! ```

use rkyv::rancor::Failure;
use rkyv::to_bytes;

use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
use crate::service::CoreIpcService;
use crate::structs::TrezorProgressEnum;
use crate::util::Timeout;
use crate::{Error, Result};

// ============================================================================
// Data types
// ============================================================================

/// How much work there is, which decides what the person sees.
///
/// The app says what it is about to do; the library turns that into the
/// bar — a growing fill when the total is known, motion without a fill
/// when it is not.
#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Total {
    /// Known upfront, in whatever unit the app counts. The percent is the
    /// library's to compute; the app never does that arithmetic.
    Units(u32),
    /// Not known upfront. The person sees that work is ongoing, and nothing
    /// else — no fill, no percent, no false promise of how much is left.
    Unknown,
}

/// A progress that is running. Dismissing it is not the app's to do: it goes
/// away when this value is dropped, whatever happened to the work.
///
/// Created by [`progress`], [`progress_with`], or [`Progress::start`]; see
/// the module docs.
pub struct Progress {
    /// Total units, when known; the percent comes from this.
    total: Option<u32>,
    /// Units reported so far.
    done: u32,
    /// Set once the initial request has been accepted, so `Drop` only ends
    /// a progress that truly started.
    started: bool,
}

// ============================================================================
// Entry point
// ============================================================================

/// Runs `work` under a progress of the given label, and returns what it
/// returns.
///
/// The progress appears before `work` runs and disappears after — on success,
/// on error, on early return through `?`, all the same, because its lifetime
/// is the call. If `work` wants to report steps, take the second form,
/// [`progress_with`].
///
/// Use [`Total::Unknown`] when the amount of work is not known upfront; the
/// person sees ongoing motion rather than a bar.
///
/// # Errors
///
/// `Err` only if the progress could not be shown at all — the request never
/// reached core, or core refused it. `work`'s own result passes through
/// untouched.
pub fn progress<T>(label: &str, total: Total, work: impl FnOnce() -> T) -> Result<T> {
    let _guard = Progress::start(label, total)?;
    Ok(work())
}

/// Runs `work` under a progress, handing it the [`Progress`] to report steps
/// with.
///
/// Same lifetime as [`progress`]; the only difference is that `work` receives
/// the handle, so it can call [`Progress::step`] as it goes.
///
/// # Errors
///
/// See [`progress`]; `work`'s own result and errors pass through untouched.
pub fn progress_with<T>(
    label: &str,
    total: Total,
    work: impl FnOnce(&mut Progress) -> T,
) -> Result<T> {
    let mut guard = Progress::start(label, total)?;
    Ok(work(&mut guard))
}

impl Progress {
    /// Starts a progress and returns it, running.
    ///
    /// Prefer [`progress`] or [`progress_with`], which tie the progress to a
    /// scope and cannot leak it; reach for this only when the work cannot be
    /// expressed as a closure. Dropping the value ends the progress — so the
    /// binding must hold it: `let _ = Progress::start(..)` drops it at once,
    /// ending the progress before any work runs. Bind it (`let _p = ..`) and
    /// let scope end do the rest.
    ///
    /// # Errors
    ///
    /// [`crate::Error::ServiceError`] if the request could not be sent or
    /// core did not accept it.
    pub fn start(label: &str, total: Total) -> Result<Self> {
        let request = TrezorProgressEnum::Init {
            description: Some(label.into()),
            title: None,
            indeterminate: matches!(total, Total::Unknown),
            danger: false,
        };
        send(&request)?;

        Ok(Self {
            total: match total {
                Total::Units(units) => Some(units),
                Total::Unknown => None,
            },
            done: 0,
            started: true,
        })
    }

    /// Reports that `units` of work are done, of the total given at the start.
    ///
    /// Deliberately infallible: an update is a status note, not a step of the
    /// work, and a status note that cannot be delivered must not abort the
    /// work it describes. The person at worst sees a stale bar until the next
    /// update or the end.
    ///
    /// Does nothing for a [`Total::Unknown`] progress — there is no fill to
    /// grow, and no number that would mean anything.
    pub fn step(&mut self, units: u32) {
        let Some(total) = self.total else { return };
        if total == 0 {
            return;
        }
        // Saturating: reporting past the declared total pins the bar full
        // rather than wrapping it around.
        self.done = self.done.saturating_add(units);
        let percent = (self.done.min(total) * 100) / total;
        let request = TrezorProgressEnum::Update {
            description: None,
            value: percent,
        };
        let _ = send(&request);
    }
}

impl Drop for Progress {
    fn drop(&mut self) {
        if self.started {
            // Nothing useful can be done if this fails, and a panic here
            // would replace whatever error is already unwinding out.
            let _ = send(&TrezorProgressEnum::End);
        }
    }
}

// ============================================================================
// Internals
// ============================================================================

/// Sends one progress message and waits for core's acknowledgement.
fn send(request: &TrezorProgressEnum) -> Result<()> {
    let bytes = to_bytes::<Failure>(request).map_err(|_| Error::ServiceError)?;
    let message = IpcMessage::new(request.id(), bytes.as_ref());
    services_or_die().call(CoreIpcService::Progress, &message, Timeout::max())?;
    Ok(())
}
