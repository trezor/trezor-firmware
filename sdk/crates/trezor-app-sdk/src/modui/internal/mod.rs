//! The library's own machinery: how a block reaches core and what happens
//! between its screens. Private to `modui`; nothing here is visible to an app.

pub(in crate::modui) mod chunked;
pub(in crate::modui) mod data;
pub(in crate::modui) mod menu;
pub(in crate::modui) mod transport;

use transport::LayoutHandle;

use super::ExtraItem;
use crate::traits::ui::UiReply;
use crate::{Error, Result};

// ============================================================================
// Constants
// ============================================================================

/// The `ButtonRequestType` every block sends: `Other`, and nothing else.
///
/// Named for its value rather than its role, so that a call site says what
/// goes on the wire instead of implying there is a choice to make.
///
/// Legacy field, kept because hosts written before `br_name` switch on it. It
/// does not classify an extapp's screens and is not meant to: the name carries
/// the meaning, and every extapp call is `Other` by decision.
///
/// Stated once here rather than per block so that the day the field leaves the
/// wire, this constant and its uses go with it and nothing has to be
/// re-derived. Do not grow it into a per-block table.
pub(in crate::modui) const BR_CODE_OTHER: i32 = 1;

// ============================================================================
// Internals
// ============================================================================

/// Sends a block and returns what the person did with it.
///
/// When a block offers extras, looking at them and coming back brings the same
/// screen up again. The layout is reopened rather than rebuilt, so it is
/// found as the person left it; that is invisible to the caller either way,
/// because the block is still one call and one answer.
pub(in crate::modui) fn call(
    request: &impl transport::Request,
    extras: &[ExtraItem<'_>],
    cancel: bool,
    refusable: bool,
    br: Option<&str>,
) -> Result<UiReply> {
    // `None` is a block that announces nothing, which is the block's own
    // nature. An empty name is neither that nor a name, so it is a mistake:
    // the host would see a step with no identity, which is worse than silence.
    if br == Some("") {
        return Err(Error::ValueError("a step name must not be empty"));
    }
    menu::check_extras(extras, cancel || refusable)?;

    let layout = LayoutHandle::new();
    let mut first = true;

    loop {
        let reply = if first {
            first = false;
            layout.show(request)?
        } else {
            layout.reshow(request)?
        };

        match reply {
            // The answers, passed on as they came. `ConfirmedAll` is a yes
            // with the fact that the rest was skipped attached, for screens
            // that offer the skip.
            UiReply::Confirmed | UiReply::Cancelled | UiReply::ConfirmedAll => return Ok(reply),
            // The person asked for the extras. A block that offered none cannot
            // produce this, so it is a protocol violation rather than a gesture.
            UiReply::WantsMore => {
                if let Some(reply) = menu::open(extras, cancel, refusable, br)? {
                    return Ok(reply);
                }
            }
            // The rest answer a screen this is not — a page turn, a pick from
            // a list, a way back no block offers — including a variant added
            // to the wire after this was written.
            _ => return Err(Error::InvalidMessage),
        }
    }
}
