//! Implements [`trezor_app_sdk::traits::ui`]'s `UiV1` on top of
//! [`crate::wire::ipc_call`]. `ui_call` takes the request exactly as the app
//! built it, serializes it, sends it to Core's UI service and returns the
//! reply. The progress methods do the same for the progress service. There is
//! nothing to convert: the vtable carries the wire types.
//!
//! This runs on the app's task but is part of the firmware, so anything an
//! app would otherwise carry in its own binary belongs here or in core.

use rkyv::rancor::Failure;
use trezor_app_sdk::structs::{TrezorProgressEnum, TrezorUiEnum};
use trezor_app_sdk::traits::ui::{StrSlice, TrezorUiResult, UiV1};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::WireError;

use crate::wire::{CoreIpcService, ipc_call, to_bytes};

/// Serializes `request`, sends it to Core's UI service and waits for the
/// request's final answer.
fn ui_request(request: TrezorUiEnum) -> Result<TrezorUiResult, WireError> {
    let bytes = to_bytes(&request).map_err(|_| WireError::DecodeError)?;
    let (_id, data) = ipc_call(CoreIpcService::Ui.into(), 0, &bytes, TIMEOUT_MAX)?;
    let archived = rkyv::access::<rkyv::Archived<TrezorUiResult>, Failure>(&data)
        .map_err(|_| WireError::DecodeError)?;
    rkyv::api::low::deserialize::<TrezorUiResult, Failure>(archived)
        .map_err(|_| WireError::DecodeError)
}

fn ipc_progress_call(value: &TrezorProgressEnum) -> Result<(), WireError> {
    let bytes = to_bytes(value).map_err(|_| WireError::DecodeError)?;
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
    extern "C" fn ui_call<'a>(
        &self,
        request: TrezorUiEnum<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        ui_request(request).into()
    }

    extern "C" fn init_progress<'a>(
        &self,
        label: StrSlice<'a>,
        total: u32,
    ) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::Init { label, total }).into()
    }

    extern "C" fn step_progress(&self, units: u32) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::Step { units }).into()
    }

    extern "C" fn label_progress<'a>(&self, label: StrSlice<'a>) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::Label { label }).into()
    }

    extern "C" fn end_progress(&self) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::End).into()
    }
}
