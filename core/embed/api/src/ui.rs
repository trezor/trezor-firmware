//! Implements [`trezor_app_sdk::traits::ui`]'s `UiV1` on top of
//! [`crate::wire::ipc_call`]. Each method takes the request exactly as the app
//! built it, serializes it, sends it to Core's UI/progress service and returns
//! the reply. There is nothing to convert: the vtable carries the wire types.

use rkyv::rancor::Failure;
use rkyv::to_bytes;
use trezor_app_sdk::structs::{TrezorProgressEnum, TrezorUiEnum};
use trezor_app_sdk::traits::ui::{
    ConfirmAction, ConfirmProperties, ConfirmSummary, ConfirmValue, OptStrSlice, ShowNotice,
    UiReply, UiV1,
};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::WireError;

use crate::wire::{CoreIpcService, ipc_call};

/// Serializes `request`, sends it to Core's UI service and waits for the
/// block's final answer.
fn ui_call(request: TrezorUiEnum) -> FastResult<UiReply, WireError> {
    let reply = || -> Result<UiReply, WireError> {
        let bytes = to_bytes::<Failure>(&request).map_err(|_| WireError::DecodeError)?;
        let (_id, data) = ipc_call(CoreIpcService::Ui.into(), 0, &bytes, TIMEOUT_MAX)?;
        let archived = rkyv::access::<rkyv::Archived<UiReply>, Failure>(&data)
            .map_err(|_| WireError::DecodeError)?;
        rkyv::api::low::deserialize::<UiReply, Failure>(archived)
            .map_err(|_| WireError::DecodeError)
    };
    reply().into()
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
        value: ConfirmAction<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(TrezorUiEnum::ConfirmAction(value))
    }

    extern "C" fn confirm_value<'a>(
        &self,
        value: ConfirmValue<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(TrezorUiEnum::ConfirmValue(value))
    }

    extern "C" fn confirm_summary<'a>(
        &self,
        value: ConfirmSummary<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(TrezorUiEnum::ConfirmSummary(value))
    }

    extern "C" fn confirm_properties<'a>(
        &self,
        value: ConfirmProperties<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(TrezorUiEnum::ConfirmProperties(value))
    }

    extern "C" fn show_notice<'a>(&self, value: ShowNotice<'a>) -> FastResult<UiReply, WireError> {
        ui_call(TrezorUiEnum::ShowNotice(value))
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
