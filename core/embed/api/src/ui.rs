//! Implements [`trezor_app_sdk::traits::ui`]'s `UiV1` on top of
//! [`crate::wire::ipc_call`]. Each method takes the request exactly as the app
//! built it, serializes it, sends it to Core's UI/progress service and returns
//! the reply. There is nothing to convert: the vtable carries the wire types.
//!
//! The op and the layout handle ride in the IPC message id;
//! `apps/extapp/run.py` unpacks them.

use rkyv::rancor::Failure;
use rkyv::to_bytes;
use trezor_app_sdk::structs::{TrezorProgressEnum, TrezorUiEnum};
use trezor_app_sdk::traits::ui::{
    ConfirmAction, ConfirmProperties, ConfirmSummary, ConfirmValue, HANDLE_BITS, OptStrSlice,
    SelectMenu, ShowNotice, ShowProperties, UiReply, UiV1,
};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::WireError;

use crate::wire::{CoreIpcService, ipc_call};

/// Drop the layout held under the handle. Core-side only: apps reach it
/// through [`UiV1::close`].
const OP_CLOSE: u16 = 3;

/// Packs an operation and a layout handle into the 16-bit IPC message id.
fn message_id(op: u16, handle: u16) -> u16 {
    (op << HANDLE_BITS) | (handle & ((1 << HANDLE_BITS) - 1))
}

/// Sends one UI message to Core and returns its reply.
fn ipc_ui_raw(op: u16, handle: u16, payload: &[u8]) -> Result<UiReply, WireError> {
    let id = message_id(op, handle);
    let (_id, data) = ipc_call(CoreIpcService::Ui.into(), id, payload, TIMEOUT_MAX)?;
    let archived = rkyv::access::<rkyv::Archived<UiReply>, Failure>(&data)
        .map_err(|_| WireError::DecodeError)?;
    rkyv::api::low::deserialize::<UiReply, Failure>(archived).map_err(|_| WireError::DecodeError)
}

/// Serializes `request` and sends it to Core's UI service.
fn ui_call(op: u16, handle: u16, request: TrezorUiEnum) -> FastResult<UiReply, WireError> {
    to_bytes::<Failure>(&request)
        .map_err(|_| WireError::DecodeError)
        .and_then(|bytes| ipc_ui_raw(op, handle, &bytes))
        .into()
}

fn ipc_progress_call(value: &TrezorProgressEnum) -> Result<(), WireError> {
    let bytes = to_bytes::<Failure>(value).map_err(|_| WireError::DecodeError)?;
    ipc_call(
        CoreIpcService::Progress.into(),
        value.id(),
        &bytes,
        TIMEOUT_MAX,
    )?;
    Ok(())
}

pub struct TrezorUiV1Impl;

impl UiV1 for TrezorUiV1Impl {
    extern "C" fn confirm_action<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmAction<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(op, handle, TrezorUiEnum::ConfirmAction(value))
    }

    extern "C" fn confirm_value<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmValue<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(op, handle, TrezorUiEnum::ConfirmValue(value))
    }

    extern "C" fn confirm_summary<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmSummary<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(op, handle, TrezorUiEnum::ConfirmSummary(value))
    }

    extern "C" fn confirm_properties<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmProperties<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(op, handle, TrezorUiEnum::ConfirmProperties(value))
    }

    extern "C" fn show_properties<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ShowProperties<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(op, handle, TrezorUiEnum::ShowProperties(value))
    }

    extern "C" fn show_notice<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ShowNotice<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(op, handle, TrezorUiEnum::ShowNotice(value))
    }

    extern "C" fn select_menu<'a>(
        &self,
        op: u16,
        handle: u16,
        value: SelectMenu<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(op, handle, TrezorUiEnum::SelectMenu(value))
    }

    extern "C" fn close(&self, handle: u16) -> FastResult<(), WireError> {
        ipc_ui_raw(OP_CLOSE, handle, &[]).map(|_| ()).into()
    }

    extern "C" fn init_progress<'a>(
        &self,
        description: OptStrSlice<'a>,
        title: OptStrSlice<'a>,
        indeterminate: bool,
        danger: bool,
    ) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::Init {
            description,
            title,
            indeterminate,
            danger,
        })
        .into()
    }

    extern "C" fn update_progress<'a>(
        &self,
        description: OptStrSlice<'a>,
        value: u32,
    ) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::Update { description, value }).into()
    }

    extern "C" fn end_progress(&self) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::End).into()
    }
}
