//! The `UiV1` vtable: how an app reaches Core's UI and progress screens.
//!
//! Every request type is a `crate::structs` type that is both stabby (so it
//! crosses this vtable as is) and rkyv (so `core/embed/api` serializes that
//! same value for IPC). There are no mirror types and no conversions.

use super::util::FastResult;
use super::wire::WireError;
pub use crate::structs::{ConfirmData, StrSlice, TrezorUiEnum, TrezorUiResult};

/// Talks to Core's UI/progress screens — implemented in `core/embed/api`
/// against [`super::wire::WireV1`].
#[stabby::stabby(checked)]
pub trait UiV1: Send + Sync {
    /// Shows one block and returns once the person has decided it. Everything
    /// in between, such as the block's menu and extras, happens in Core.
    extern "C" fn ui_call<'a>(
        &self,
        request: TrezorUiEnum<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    /// Shows all of `request.data`, however long; the implementation sends it
    /// to core in chunks.
    extern "C" fn confirm_data<'a>(
        &self,
        request: ConfirmData<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;

    /// `total` is in the app's own units; `0` means not known.
    extern "C" fn init_progress<'a>(
        &self,
        label: StrSlice<'a>,
        total: u32,
    ) -> FastResult<(), WireError>;
    /// Reports `units` more of the total done.
    extern "C" fn step_progress(&self, units: u32) -> FastResult<(), WireError>;
    extern "C" fn end_progress(&self) -> FastResult<(), WireError>;
}

pub type UiV1Vtable = stabby::vtable!(UiV1 + Send + Sync);
pub type UiV1Ref<'a> = stabby::DynRef<'a, UiV1Vtable>;
pub type StaticUiV1 = UiV1Ref<'static>;
