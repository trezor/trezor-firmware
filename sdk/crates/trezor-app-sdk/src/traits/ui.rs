//! The `UiV1` vtable: how an app reaches Core's UI and progress screens.
//!
//! Every request type is a `crate::structs` type that is both stabby (so it
//! crosses this vtable as is) and rkyv (so `core/embed/api` serializes that
//! same value for IPC). There are no mirror types and no conversions.

use super::util::FastResult;
use super::wire::WireError;
pub use crate::structs::{
    ConfirmAction, ConfirmProperties, ConfirmSummary, ConfirmValue, ExtraItem, OptStrSlice,
    Property, Severity, ShowNotice, UiReply,
};

/// Talks to Core's UI/progress screens — implemented in `core/embed/api`
/// against [`super::wire::WireV1`].
///
/// Each screen method shows one block and returns once the person has decided
/// it. Everything in between, such as the block's menu and extras, happens in
/// Core.
#[stabby::stabby(checked)]
pub trait UiV1: Send + Sync {
    extern "C" fn confirm_action<'a>(
        &self,
        value: ConfirmAction<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn confirm_value<'a>(
        &self,
        value: ConfirmValue<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn confirm_summary<'a>(
        &self,
        value: ConfirmSummary<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn confirm_properties<'a>(
        &self,
        value: ConfirmProperties<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn show_notice<'a>(&self, value: ShowNotice<'a>) -> FastResult<UiReply, WireError>;

    extern "C" fn init_progress<'a>(
        &self,
        description: OptStrSlice<'a>,
        title: OptStrSlice<'a>,
        indeterminate: bool,
        danger: bool,
    ) -> FastResult<(), WireError>;
    /// `value` is how far along, from 0 to 1000.
    extern "C" fn update_progress<'a>(
        &self,
        description: OptStrSlice<'a>,
        value: u32,
    ) -> FastResult<(), WireError>;
    extern "C" fn end_progress(&self) -> FastResult<(), WireError>;
}

pub type UiV1Vtable = stabby::vtable!(UiV1 + Send + Sync);
pub type UiV1Ref<'a> = stabby::DynRef<'a, UiV1Vtable>;
pub type StaticUiV1 = UiV1Ref<'static>;
