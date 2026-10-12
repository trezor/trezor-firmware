//! Implements [`trezor_app_sdk::traits::ui`]'s `UiV1` on top of
//! [`crate::wire::ipc_call`]. `ui_call` takes the request exactly as the app
//! built it, serializes it, sends it to Core's UI service and returns the
//! reply; the progress methods do the same for the progress service. There is
//! nothing to convert: the vtable carries the wire types.
//!
//! This runs on the app's task but is part of the firmware, so anything an
//! app would otherwise carry in its own binary belongs here or in core.

use rkyv::rancor::Failure;
use rkyv::to_bytes;
use trezor_app_sdk::structs::{ConfirmData, TrezorProgressEnum, TrezorUiEnum};
use trezor_app_sdk::traits::ui::{StrSlice, TrezorUiResult, UiV1};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::WireError;

use crate::wire::{CoreIpcService, ipc_call};

/// Bytes of an app's data sent to core per [`ConfirmData`] request.
///
/// Chunking bounds how much of a long blob core holds at once: core keeps a
/// few copies of a request while it shows it. Core's inbox for app messages
/// (32 KB) is the hard ceiling, far above this. Core pages each chunk itself,
/// and formats the hex only for the page on screen.
///
/// WIP: a guess. Measure core's heap with a large blob and raise it.
const BYTES_PER_CHUNK: usize = 384;

/// Serializes `request`, sends it to Core's UI service and waits for the
/// block's final answer.
fn ui_request(request: TrezorUiEnum) -> Result<TrezorUiResult, WireError> {
    let bytes = to_bytes::<Failure>(&request).map_err(|_| WireError::DecodeError)?;
    let (_id, data) = ipc_call(CoreIpcService::Ui.into(), 0, &bytes, TIMEOUT_MAX)?;
    let archived = rkyv::access::<rkyv::Archived<TrezorUiResult>, Failure>(&data)
        .map_err(|_| WireError::DecodeError)?;
    rkyv::api::low::deserialize::<TrezorUiResult, Failure>(archived)
        .map_err(|_| WireError::DecodeError)
}

/// Shows `request.data` a chunk at a time, stopping as soon as the person
/// decides.
///
/// Two things split long content, and this is only one of them. Chunking is
/// here: each chunk goes to core as a request of its own, so core never holds
/// a whole blob. Paging is core's: it splits one chunk across as many screens
/// as it takes. Today the two meet only at a chunk's edge — the person's yes
/// on a chunk's last page moves to the next chunk.
///
/// WIP, the direction: one continuous read, where the screen says when it is
/// paging past the chunk it holds and the next one is fetched before the
/// person gets there. The loop already follows the paging replies
/// (`TrezorUiResult::Forward`, `Backward`, `ConfirmedAll`); no screen sends
/// them yet.
///
/// The app gets one answer for the whole content, and cannot learn that it
/// was shown in more than one piece.
fn confirm_in_chunks(request: ConfirmData) -> Result<TrezorUiResult, WireError> {
    let data = request.data.as_slice();
    // Empty content still gets one screen, or the person confirms nothing.
    let chunk_count = data.len().div_ceil(BYTES_PER_CHUNK).max(1);
    let mut index = 0;

    // Every way out of this loop is a `return` beside the reason for it, and
    // the loop itself cannot end. That is deliberate: a confirmation must
    // never be what a loop yields by running out. `break` here, or a
    // trailing `Ok(Confirmed)` below, would mean an edit that changed how the
    // loop finishes could turn into a silent yes on a signing device.
    loop {
        let start = index * BYTES_PER_CHUNK;
        let chunk = &data[start..(start + BYTES_PER_CHUNK).min(data.len())];
        match ui_request(TrezorUiEnum::ConfirmData(ConfirmData {
            data: chunk.into(),
            ..request
        }))? {
            // Core pages within a chunk, so a yes means the person has seen
            // all of it. Accepting the last chunk is the only way to a yes by
            // reading.
            TrezorUiResult::Confirmed if index + 1 == chunk_count => {
                return Ok(TrezorUiResult::Confirmed);
            }
            TrezorUiResult::Confirmed => index += 1,
            TrezorUiResult::Cancelled => return Ok(TrezorUiResult::Cancelled),
            TrezorUiResult::Forward => index = (index + 1).min(chunk_count - 1),
            TrezorUiResult::Backward => index = index.saturating_sub(1),
            TrezorUiResult::ConfirmedAll => return Ok(TrezorUiResult::ConfirmedAll),
        }
    }
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
    extern "C" fn ui_call<'a>(
        &self,
        request: TrezorUiEnum<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        match request {
            TrezorUiEnum::ConfirmData(data) => confirm_in_chunks(data),
            request => ui_request(request),
        }
        .into()
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

    extern "C" fn end_progress(&self) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::End).into()
    }
}
