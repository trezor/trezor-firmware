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

    /// Shows the progress bar as `progress` describes it, whatever was on the
    /// screen before.
    extern "C" fn progress_v1<'a>(&self, progress: ProgressV1<'a>) -> ServiceResult<()>;
}

/// The stabby vtable of [`UiV1`].
pub type UiV1Vtable = stabby::vtable!(UiV1 + Send + Sync);
/// A borrowed `dyn UiV1`.
pub type UiV1Ref<'a> = stabby::DynRef<'a, UiV1Vtable>;
/// A `dyn UiV1` that lives as long as the app.
pub type StaticUiV1 = UiV1Ref<'static>;
