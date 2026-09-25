//! A sequence of blocks the person can go back through.
//!
//! Not a block: no screen of its own, nothing to confirm. The flow runs
//! steps the app supplies, in order, and owns only the ordering — which
//! step comes next, and which came before. What a step shows, and what it
//! asks, is entirely the step's; the flow never looks inside one.
//!
//! What makes it a flow rather than a loop the app could write itself is
//! the back bookkeeping: which steps offer a way back is decided here, in
//! one place, so the app cannot get it wrong per step. See
//! [going back](super#going-back) for the design.

use super::UiReply;
use crate::{Error, Result};

// ============================================================================
// Entry point
// ============================================================================

/// Runs confirmation steps in order, with back navigation, and returns how
/// the sequence ended.
///
/// Each element of `steps` is called with one argument: whether this step's
/// screen should offer a way back. The flow passes `false` for the first
/// step — there is nothing before it — and `true` for every one after, so
/// the app does not track position and cannot misdeclare it. The step
/// forwards the flag to its block's `back` parameter.
///
/// - A step confirmed moves to the next; the last step's yes is the flow's
///   answer, carried as it came — `ConfirmedAll` stays `ConfirmedAll`.
/// - A step refused ends the flow as refused.
/// - A `Backward` — which only a step given `back` can answer — shows the
///   step before again.
///
/// A step's `Err` propagates untouched: the flow adds no failures of its
/// own beyond the one below.
///
/// # Errors
///
/// [`crate::Error::ValueError`] when `steps` is empty. A flow that would
/// confirm by running out of steps is a yes nobody gave, and refusing the
/// empty list is cheaper than debating it at every call site.
///
/// WIP: `Backward` cannot arrive yet — no block takes `back`, so no screen
/// offers the gesture and the third bullet is dormant. The arm is written,
/// so landing the parameter changes no line here.
///
/// # Example
///
/// ```text
/// ui::confirm_linear_flow(&[
///     |back| ui::confirm_value(ConfirmValue::new(.., back, ..)),
///     |back| ui::confirm_summary(ConfirmSummary::new(.., back, ..)),
/// ])?;
/// ```
pub fn confirm_linear_flow(steps: &[&dyn Fn(bool) -> Result<UiReply>]) -> Result<UiReply> {
    if steps.is_empty() {
        return Err(Error::ValueError("a flow needs at least one step"));
    }

    let mut i = 0;
    loop {
        // `back` is the flow's to give: false for the first step, true for
        // the rest. A step cannot ask for it on its own, so the first step
        // can never answer `Backward` — the guard is structural, not a
        // runtime check.
        let reply = steps[i](i > 0)?;
        match reply {
            UiReply::Confirmed | UiReply::ConfirmedAll => {
                if i + 1 == steps.len() {
                    return Ok(reply);
                }
                i += 1;
            }
            // Arrives only from a step that was given `back`, hence never
            // from the first; `i` cannot reach 0 with this arm.
            UiReply::Backward => i -= 1,
            UiReply::Cancelled => return Ok(UiReply::Cancelled),
            // The rest answer a screen no step's block shows.
            _ => return Err(Error::InvalidMessage),
        }
    }
}
