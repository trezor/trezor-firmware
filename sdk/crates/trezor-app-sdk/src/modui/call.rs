//! The one wire call every layout makes, and how its answers are read.
//!
//! Private: a layout builds its request, calls [`call`], and maps the answer
//! with [`yes_or_no`]. Nothing here is the app's to use.

use spin::Mutex;

use crate::app_runtime::{get_ui_or_die, system_exit_fatal};
use crate::structs::{TrezorUiEnum, TrezorUiResult};
use crate::traits::ui::UiV1Dyn as _;
use crate::{Error, Result};

/// The error a data source returned during the last call, until its answer is
/// read.
///
/// Core only learns that a read failed, not why: the app's source kept the
/// reason, and this slot hands it back in place of a cancel.
static SOURCE_ERROR: Mutex<Option<Error>> = Mutex::new(None);

/// Keeps `error` for the answer of the call that is running.
pub(crate) fn set_source_error(error: Error) {
    *SOURCE_ERROR.lock() = Some(error);
}

/// Takes the error a data source returned during the last call, if any.
pub(crate) fn take_source_error() -> Option<Error> {
    SOURCE_ERROR.lock().take()
}

/// Shows one request and returns the person's answer.
///
/// A request that cannot reach core ends the app: there is nothing the app could
/// do about it, and the layout has no answer to give.
pub(crate) fn call<'a>(request: TrezorUiEnum<'a>) -> TrezorUiResult {
    // A source that failed on the last call must not fail this one.
    take_source_error();
    match get_ui_or_die().ui_call(request).into_result() {
        Ok(result) => result,
        Err(e) => system_exit_fatal(e.message(), file!(), line!()),
    }
}

/// Reads a layout's answer as a yes or a no.
///
/// `Ok(())` for a yes, `Err(Error::Cancelled)` for a no, and the data source's
/// own error when a read failed. Any other answer is a failure of the request:
/// the screen did not ask what the layout asked.
pub(crate) fn yes_or_no(result: TrezorUiResult) -> Result<()> {
    match result {
        TrezorUiResult::Confirmed => Ok(()),
        TrezorUiResult::Cancelled => Err(take_source_error().unwrap_or(Error::Cancelled)),
        _ => Err(Error::DataError("unexpected UI answer")),
    }
}
