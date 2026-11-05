//! Implements [`trezor_app_sdk::traits::ui`]'s `UiV1` on top of
//! [`crate::wire::ipc_call`]. `ui_call` takes the request exactly as the app
//! built it, serializes it, sends it to Core's UI service and returns the
//! reply. The progress methods do the same for the progress service. There is
//! nothing to convert: the vtable carries the wire types.
//!
//! A `Data` field travels as its length alone, so Core pulls the bytes from the
//! app while the person pages: `ui_call` answers Core's chunk requests from the
//! request's own source, and returns only the final decision. A source that
//! cannot produce a range answers with the chunk-failed id instead, and Core
//! stops the layout.
//!
//! This runs on the app's task but is part of the firmware, so anything an
//! app would otherwise carry in its own binary belongs here or in core.

use rkyv::rancor::Failure;
use trezor_app_sdk::structs::{
    Source, TrezorProgressEnum, TrezorUiEnum, UI_MSG_CHUNK, UI_MSG_CHUNK_FAILED, UI_MSG_DECISION,
    UiChunkRequest,
};
use trezor_app_sdk::traits::ui::{StrSlice, TrezorUiResult, UiV1};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::WireError;

use crate::wire::{CoreIpcService, ipc_call, to_bytes};

/// Reads a chunk request: the field's flat index, the offset and the length.
fn chunk_request(data: &[u8]) -> Option<UiChunkRequest> {
    let archived = rkyv::access::<rkyv::Archived<UiChunkRequest>, Failure>(data).ok()?;
    Some(UiChunkRequest {
        field: archived.field.to_native(),
        offset: archived.offset.to_native(),
        len: archived.len.to_native(),
    })
}

/// The source of the `Data` field at flat index `index`, if there is one.
///
/// The index counts the review's own fields first, then each extra's fields in
/// order — every field counts, whatever its kind, and only a `Data` field has
/// bytes to give.
fn data_field<'a>(request: &TrezorUiEnum<'a>, index: u16) -> Option<Source<'a>> {
    let TrezorUiEnum::Review(review) = request else {
        return None;
    };
    let extras = review.extras.as_slice().iter();
    review
        .fields
        .as_slice()
        .iter()
        .chain(extras.flat_map(|extra| extra.fields.as_slice()))
        .nth(index as usize)?
        .source
}

/// Serializes `request`, sends it to Core's UI service and waits for the
/// request's final answer, answering Core's chunk requests on the way.
fn ui_request(request: TrezorUiEnum) -> Result<TrezorUiResult, WireError> {
    let bytes = to_bytes(&request).map_err(|_| WireError::DecodeError)?;
    let (mut id, mut data) = ipc_call(
        CoreIpcService::Ui.into(),
        UI_MSG_DECISION,
        &bytes,
        TIMEOUT_MAX,
    )?;

    loop {
        match id {
            UI_MSG_DECISION => {
                let archived = rkyv::access::<rkyv::Archived<TrezorUiResult>, Failure>(&data)
                    .map_err(|_| WireError::DecodeError)?;
                return rkyv::api::low::deserialize::<TrezorUiResult, Failure>(archived)
                    .map_err(|_| WireError::DecodeError);
            }
            UI_MSG_CHUNK => {
                let chunk = chunk_request(&data).ok_or(WireError::DecodeError)?;
                let source = data_field(&request, chunk.field).ok_or(WireError::DecodeError)?;
                let mut bytes = alloc::vec![0u8; chunk.len as usize];
                let (next_id, next_data) = if source.read(chunk.offset, &mut bytes) {
                    ipc_call(CoreIpcService::Ui.into(), UI_MSG_CHUNK, &bytes, TIMEOUT_MAX)?
                } else {
                    // The app's source could not produce the range. Core stops
                    // the layout, and the next message is the cancel it sends.
                    ipc_call(
                        CoreIpcService::Ui.into(),
                        UI_MSG_CHUNK_FAILED,
                        &[],
                        TIMEOUT_MAX,
                    )?
                };
                id = next_id;
                data = next_data;
            }
            _ => return Err(WireError::DecodeError),
        }
    }
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
