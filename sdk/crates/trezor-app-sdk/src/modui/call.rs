//! The one wire call every layout makes, and how its answers are read.
//!
//! Private: a layout builds its request, calls [`call`], and maps the answer
//! with [`yes_or_no`]. Nothing here is the app's to use.

use crate::app_runtime::{get_ui_or_die, system_exit_fatal};
use crate::structs::{TrezorUiEnum, TrezorUiResult};
use crate::traits::ui::UiV1Dyn as _;
use crate::{Error, Result};

/// Shows one request and returns the person's answer.
///
/// A request that cannot reach core ends the app: there is nothing the app could
/// do about it, and the layout has no answer to give.
pub(crate) fn call<'a>(request: TrezorUiEnum<'a>) -> TrezorUiResult {
    match get_ui_or_die().ui_call(request).into_result() {
        Ok(result) => result,
        Err(e) => system_exit_fatal(e.message(), file!(), line!()),
    }
}

/// Reads a layout's answer as a yes or a no.
///
/// `Ok(())` for a yes, `Err(Error::Cancelled)` for a no. Any other answer is a
/// failure of the request: the screen did not ask what the layout asked.
pub(crate) fn yes_or_no(result: TrezorUiResult) -> Result<()> {
    match result {
        TrezorUiResult::Confirmed => Ok(()),
        TrezorUiResult::Cancelled => Err(Error::Cancelled),
        _ => Err(Error::DataError("unexpected UI answer")),
    }
}
