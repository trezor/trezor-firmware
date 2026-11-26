//! The `UiV1` vtable: how an app reaches Core's UI and progress screens, and
//! the request types it carries.
//!
//! Every request type is both stabby (so it crosses this vtable as is) and
//! rkyv (so `core/embed/api` serializes that same value for IPC).
//!
//! A method and the type it takes are versioned together: a request type that
//! changes beyond its reserved room becomes `…V2`, taken by a new `…_v2`
//! method next to the old one, so apps built against `…V1` keep working.

#[cfg(test)]
mod abi;
mod types;

pub use types::*;

use super::util::ServiceResult;
use crate::structs::StrSlice;

/// Talks to Core's UI/progress screens — implemented in `core/embed/api`
/// against [`super::wire::WireV1`].
#[stabby::stabby(checked)]
pub trait UiV1: Send + Sync {
    /// Shows one request and returns once the person has decided it. Everything
    /// in between, such as the request's menu and extras, happens in Core.
    extern "C" fn ui_call_v1<'a>(
        &self,
        request: TrezorUiEnumV1<'a>,
    ) -> ServiceResult<TrezorUiResultV1>;

    /// `total` is in the app's own units; `0` means not known.
    extern "C" fn init_progress<'a>(&self, label: StrSlice<'a>, total: u32) -> ServiceResult<()>;
    /// Reports `units` more of the total done.
    extern "C" fn step_progress(&self, units: u32) -> ServiceResult<()>;
    /// Changes the text under the bar while the work goes on.
    extern "C" fn label_progress<'a>(&self, label: StrSlice<'a>) -> ServiceResult<()>;
    /// Closes the progress indicator.
    extern "C" fn end_progress(&self) -> ServiceResult<()>;
}

/// The stabby vtable of [`UiV1`].
pub type UiV1Vtable = stabby::vtable!(UiV1 + Send + Sync);
/// A borrowed `dyn UiV1`.
pub type UiV1Ref<'a> = stabby::DynRef<'a, UiV1Vtable>;
/// A `dyn UiV1` that lives as long as the app.
pub type StaticUiV1 = UiV1Ref<'static>;
