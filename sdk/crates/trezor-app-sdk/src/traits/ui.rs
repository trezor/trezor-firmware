//! The `UiV1` vtable: how an app reaches Core's UI and progress screens.
//!
//! Every request type is a `crate::structs` type that is both stabby (so it
//! crosses this vtable as is) and rkyv (so `core/embed/api` serializes that
//! same value for IPC). There are no mirror types and no conversions.

use super::util::FastResult;
use super::wire::WireError;
pub use crate::structs::{
    ConfirmAction, ConfirmProperties, ConfirmSummary, ConfirmValue, OptStrSlice, Property,
    SelectMenu, Severity, ShowNotice, ShowProperties, UiReply,
};

/// Build a layout, show it, and forget it. The handle is ignored.
pub const OP_ONCE: u16 = 0;
/// Build a layout and keep it alive under the handle.
pub const OP_OPEN: u16 = 1;
/// Show the layout already held under the handle, without rebuilding it.
pub const OP_REOPEN: u16 = 2;
/// Bits a handle may use; Core packs it with the op into one IPC message id.
pub const HANDLE_BITS: u16 = 12;

/// Talks to Core's UI/progress screens — implemented in `core/embed/api`
/// against [`super::wire::WireV1`].
///
/// Each screen method sends one request and returns Core's reply. `op` is one
/// of [`OP_ONCE`], [`OP_OPEN`], [`OP_REOPEN`]; `handle` names the layout Core
/// keeps for the last two, until [`UiV1::close`].
#[stabby::stabby(checked)]
pub trait UiV1: Send + Sync {
    extern "C" fn confirm_action<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmAction<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn confirm_value<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmValue<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn confirm_summary<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmSummary<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn confirm_properties<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmProperties<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn show_properties<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ShowProperties<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn show_notice<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ShowNotice<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn select_menu<'a>(
        &self,
        op: u16,
        handle: u16,
        value: SelectMenu<'a>,
    ) -> FastResult<UiReply, WireError>;
    /// Drops the layout held under `handle`. Shows nothing.
    extern "C" fn close(&self, handle: u16) -> FastResult<(), WireError>;

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
