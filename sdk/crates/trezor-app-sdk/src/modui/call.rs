//! The one wire call every layout makes, and how its answers are read.
//!
//! Private: a layout builds its request, calls [`call`], and reads the answer.
//! Nothing here is the app's to use.

use spin::Mutex;

use crate::app_runtime::get_ui_or_die;
use crate::structs::{TrezorUiEnum, TrezorUiResult};
use crate::traits::ui::UiV1Dyn as _;
use crate::{Error, IntoAppResult, Result};

/// The error a text source returned during the last call, until its answer is
/// read.
///
/// Core only learns that a read failed, not why: the app's source kept the
/// reason, and this slot hands it back in place of a cancel.
static SOURCE_ERROR: Mutex<Option<Error>> = Mutex::new(None);

/// Keeps `error` for the answer of the call that is running.
pub(crate) fn set_source_error(error: Error) {
    *SOURCE_ERROR.lock() = Some(error);
}

/// Takes the error a text source returned during the last call, if any.
fn take_source_error() -> Option<Error> {
    SOURCE_ERROR.lock().take()
}

/// The person's answer to a request, once a refusal has become an `Err`.
pub(crate) enum Decision {
    Confirmed,
    ShowDetails,
}

/// Shows one request and returns the person's answer.
///
/// A refusal is `Err(Error::Cancelled)`, or the text source's own error when a
/// read failed and core stopped the screen. Core asking the app to stop is
/// `Err(Error::Stopped)`, and a request that cannot reach core is
/// `Err(Error::ServiceError)`; both unwind to the app's entry point.
pub(crate) fn call(request: TrezorUiEnum<'_>) -> Result<Decision> {
    // A source that failed on the last call must not fail this one.
    take_source_error();
    match get_ui_or_die().ui_call(request).into_app_result()? {
        TrezorUiResult::Confirmed => Ok(Decision::Confirmed),
        TrezorUiResult::ShowDetails => Ok(Decision::ShowDetails),
        TrezorUiResult::Cancelled => Err(take_source_error().unwrap_or(Error::Cancelled)),
    }
}

/// Reads an answer that can only be a yes.
///
/// "Show all" is an answer to a request that did not offer it: core's fault,
/// not the person's or the app's.
pub(crate) fn confirmed(decision: Decision) -> Result<()> {
    match decision {
        Decision::Confirmed => Ok(()),
        Decision::ShowDetails => Err(Error::ServiceError),
    }
}

#[cfg(all(test, feature = "test"))]
mod tests {
    use super::*;
    use crate::structs::DoneRequest;

    #[test]
    fn a_stop_from_core_unwinds_instead_of_ending_the_app() {
        // The mock's core has asked the app to stop.
        crate::mock::sdk_init();
        let request = TrezorUiEnum::Done(DoneRequest {
            step: "test/done".into(),
            text: "Done".into(),
        });
        assert!(matches!(call(request), Err(Error::Stopped)));
    }
}
