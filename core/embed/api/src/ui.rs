//! Implements [`trezor_app_sdk::traits::ui`]'s `UiV1` on top of
//! [`crate::wire::ipc_call`]. `ui_call_v1` takes the request exactly as the app
//! built it, serializes it, sends it to Core's UI service and returns the
//! reply. `progress_v1` does the same for the progress service. There is
//! nothing to convert: the vtable carries the wire types.
//!
//! A `TextSource` field travels as its length alone, so Core pulls the text
//! from the app while the person pages: `ui_call_v1` answers Core's chunk
//! requests from the request's own source, and returns only the final decision.
//! A source that cannot produce a range answers with the chunk-failed id
//! instead, and Core stops the layout.
//!
//! This runs on the app's task but is part of the firmware, so anything an
//! app would otherwise carry in its own binary belongs here or in core.

use rkyv::api::high::{HighDeserializer, HighValidator};
use rkyv::bytecheck::CheckBytes;
use rkyv::rancor::Failure;
use rkyv::{Archive, Deserialize};
use trezor_app_sdk::traits::ui::{
    PROGRESS_MSG, ProgressV1, SourceRef, TrezorUiEnumV1, TrezorUiResultV1, UI_MSG_CHUNK,
    UI_MSG_CHUNK_FAILED, UI_MSG_DECISION, UiChunkRequest, UiV1, WireField,
};
use trezor_app_sdk::traits::util::{ServiceResult, TIMEOUT_MAX};

use crate::wire::{CallError, CoreIpcService, call_failed, ipc_call, to_bytes};

/// Reads one of core's UI messages.
fn decode<T: Archive>(data: &[u8], what: &str) -> Result<T, CallError>
where
    T::Archived:
        for<'a> CheckBytes<HighValidator<'a, Failure>> + Deserialize<T, HighDeserializer<Failure>>,
{
    rkyv::from_bytes::<T, Failure>(data).map_err(|_| call_failed(what))
}

/// The source of the `TextSource` field at flat index `index`, if there is one.
///
/// The index counts the review's own fields first, then each extra's fields in
/// order — every field counts, whatever its kind, and only a `TextSource` field
/// has text to give.
fn text_source<'a>(request: &TrezorUiEnumV1<'a>, index: u16) -> Option<SourceRef<'a>> {
    let TrezorUiEnumV1::Review(review) = request else {
        return None;
    };
    let extras = review.extras.as_slice().iter();
    review
        .fields
        .as_slice()
        .iter()
        .chain(extras.flat_map(|extra| extra.fields.as_slice()))
        .nth(index as usize)
        .and_then(|field| match field {
            WireField::TextSource { source, .. } => Some(*source),
            _ => None,
        })
}

/// Serializes `request`, sends it to Core's UI service and waits for the
/// request's final answer, answering Core's chunk requests on the way.
fn ui_request(request: TrezorUiEnumV1) -> Result<TrezorUiResultV1, CallError> {
    let bytes = to_bytes(&request).map_err(|_| call_failed("failed to serialize UI request"))?;
    let ui = CoreIpcService::Ui.into();
    let (mut id, mut data) = ipc_call(ui, UI_MSG_DECISION, &bytes, TIMEOUT_MAX)?;
    let mut chunk = alloc::vec::Vec::new();
    loop {
        match id {
            UI_MSG_DECISION => return decode(&data, "failed to decode UI response"),
            UI_MSG_CHUNK => {
                let asked: UiChunkRequest = decode(&data, "failed to decode UI chunk request")?;
                let source = text_source(&request, asked.field)
                    .ok_or_else(|| call_failed("UI chunk request names no text source"))?;
                chunk.resize(asked.len as usize, 0);
                // The source runs inside this call: an `ipc_call` from it would
                // be a second call in flight, and Core stops the app for it.
                // A source that cannot produce the range answers with the
                // chunk-failed id; core stops the layout, and its next message
                // is the cancel.
                let (reply, payload): (u16, &[u8]) = if source.read(asked.offset, &mut chunk) {
                    (UI_MSG_CHUNK, &chunk)
                } else {
                    (UI_MSG_CHUNK_FAILED, &[])
                };
                (id, data) = ipc_call(ui, reply, payload, TIMEOUT_MAX)?;
            }
            _ => return Err(call_failed("unexpected UI message")),
        }
    }
}

/// Sends one progress state to Core's progress service.
fn progress_request(progress: &ProgressV1) -> Result<(), CallError> {
    let bytes =
        to_bytes(progress).map_err(|_| call_failed("failed to serialize progress request"))?;
    ipc_call(
        CoreIpcService::Progress.into(),
        PROGRESS_MSG,
        &bytes,
        TIMEOUT_MAX,
    )?;
    Ok(())
}

pub struct TrezorUiV1Impl;

impl UiV1 for TrezorUiV1Impl {
    extern "C" fn ui_call_v1<'a>(
        &self,
        request: TrezorUiEnumV1<'a>,
    ) -> ServiceResult<TrezorUiResultV1> {
        ui_request(request).into()
    }

    extern "C" fn progress_v1<'a>(&self, progress: ProgressV1<'a>) -> ServiceResult<()> {
        progress_request(&progress).into()
    }
}
