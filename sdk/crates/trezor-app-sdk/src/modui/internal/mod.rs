//! The library's own machinery. Private to `modui`; nothing here is visible to
//! an app.

pub(in crate::modui) mod chunked;
pub(in crate::modui) mod data;

use crate::traits::ui::UiReply;
use crate::{Error, Result};

/// Reads the answer of a block that waits for the person.
///
/// A yes is `Ok`. A cancel is `Err(Cancelled)`, so that `?` stops the app's
/// flow on it.
pub(in crate::modui) fn answer(reply: UiReply) -> Result<()> {
    match reply {
        UiReply::Confirmed => Ok(()),
        UiReply::Cancelled => Err(Error::Cancelled),
    }
}
