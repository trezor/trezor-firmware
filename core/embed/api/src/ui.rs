//! Implements [`trezor_app_sdk::traits::ui`]'s `UiV1` on top of
//! [`crate::wire::ipc_call`]. `ui_call` takes the request exactly as the app
//! built it, serializes it, sends it to Core's UI service and returns the
//! reply. The progress methods do the same for the progress service. There is
//! nothing to convert: the vtable carries the wire types.
//!
//! A `Data` field travels as its length alone, so Core pulls the bytes from the
//! app while the person pages: `ui_call` answers Core's chunk requests from the
//! request still in the app's memory, and returns only the final decision.
//!
//! This runs on the app's task but is part of the firmware, so anything an
//! app would otherwise carry in its own binary belongs here or in core.

use alloc::vec::Vec;

use rkyv::rancor::Failure;
use trezor_app_sdk::structs::{
    FieldKind, FieldsRequest, ReviewRequest, Slice, TrezorProgressEnum, TrezorUiEnum, WireExtra,
    WireField,
};
use trezor_app_sdk::traits::ui::{StrSlice, TrezorUiResult, UiV1};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::WireError;

use crate::wire::{CoreIpcService, ipc_call, to_bytes};

// Message ids on the UI service. A decision is the request's own id; a chunk
// request has its own so that neither is mistaken for a decision. Each chunk
// request is answered with the chunk itself, so the two alternate until core
// sends the decision.
const MSG_ID_UI_DECISION: u16 = 0;
const MSG_ID_UI_CHUNK: u16 = 1;

/// Reads a chunk request: `(field, offset, len)`, little-endian, as core packs
/// it.
fn chunk_request(data: &[u8]) -> Option<(u16, u32, u32)> {
    if data.len() != 10 {
        return None;
    }
    Some((
        u16::from_le_bytes([data[0], data[1]]),
        u32::from_le_bytes([data[2], data[3], data[4], data[5]]),
        u32::from_le_bytes([data[6], data[7], data[8], data[9]]),
    ))
}

/// What the flat index of a request names.
enum FieldAt<'a> {
    /// The index runs past every field the request carries.
    NotFound,
    /// The field at the index carries no bytes.
    NotData,
    /// The field at the index is a `Data` field, with its bytes.
    Data(&'a [u8]),
}

/// The bytes of the `Data` field at flat index `index`, if there is one.
///
/// The index counts the request's own fields first, then each extra's fields in
/// order — every field counts, whatever its kind, and only a `Data` field has
/// bytes to give.
fn data_field<'a>(request: &TrezorUiEnum<'a>, index: u16) -> Option<&'a [u8]> {
    let mut remaining = index as usize;
    match request {
        TrezorUiEnum::Review(m) => {
            match field_at(m.fields.as_slice(), &mut remaining) {
                FieldAt::Data(value) => return Some(value),
                FieldAt::NotData => return None,
                FieldAt::NotFound => {}
            }
            for extra in m.extras.as_slice() {
                match field_at(extra.fields.as_slice(), &mut remaining) {
                    FieldAt::Data(value) => return Some(value),
                    FieldAt::NotData => return None,
                    FieldAt::NotFound => {}
                }
            }
            None
        }
        TrezorUiEnum::Danger(m) | TrezorUiEnum::Details(m) => {
            match field_at(m.fields.as_slice(), &mut remaining) {
                FieldAt::Data(value) => Some(value),
                FieldAt::NotData | FieldAt::NotFound => None,
            }
        }
        TrezorUiEnum::VerifyAddress(_) | TrezorUiEnum::VerifyPubkey(_) | TrezorUiEnum::Done(_) => {
            None
        }
    }
}

/// The field at flat index `remaining`, counting from zero within `fields`.
fn field_at<'a>(fields: &'a [WireField<'a>], remaining: &mut usize) -> FieldAt<'a> {
    for field in fields {
        if *remaining == 0 {
            return if field.kind == FieldKind::Data {
                FieldAt::Data(field.value.as_slice())
            } else {
                FieldAt::NotData
            };
        }
        *remaining -= 1;
    }
    FieldAt::NotFound
}

/// Serializes `request`, sends it to Core's UI service and waits for the
/// request's final answer, answering Core's chunk requests on the way.
fn ui_request(request: TrezorUiEnum) -> Result<TrezorUiResult, WireError> {
    // Every `Data` value crosses emptied, its length kept; the request itself
    // keeps the bytes for the chunk requests below.
    let fields = emptied(fields_of(&request));
    let extra_fields: Vec<Vec<WireField>> = extras_of(&request)
        .iter()
        .map(|extra| emptied(extra.fields.as_slice()))
        .collect();
    let extras: Vec<WireExtra> = extras_of(&request)
        .iter()
        .zip(extra_fields.iter())
        .map(|(extra, fields)| WireExtra {
            label: extra.label,
            fields: Slice::new(fields),
        })
        .collect();

    let bytes =
        to_bytes(&crossing(&request, &fields, &extras)).map_err(|_| WireError::DecodeError)?;
    let (mut id, mut data) = ipc_call(
        CoreIpcService::Ui.into(),
        MSG_ID_UI_DECISION,
        &bytes,
        TIMEOUT_MAX,
    )?;

    loop {
        match id {
            MSG_ID_UI_DECISION => {
                let archived = rkyv::access::<rkyv::Archived<TrezorUiResult>, Failure>(&data)
                    .map_err(|_| WireError::DecodeError)?;
                return rkyv::api::low::deserialize::<TrezorUiResult, Failure>(archived)
                    .map_err(|_| WireError::DecodeError);
            }
            MSG_ID_UI_CHUNK => {
                let (field, offset, len) = chunk_request(&data).ok_or(WireError::DecodeError)?;
                let value = data_field(&request, field).ok_or(WireError::DecodeError)?;
                let start = (offset as usize).min(value.len());
                let end = start.saturating_add(len as usize).min(value.len());
                let (next_id, next_data) = ipc_call(
                    CoreIpcService::Ui.into(),
                    MSG_ID_UI_CHUNK,
                    &value[start..end],
                    TIMEOUT_MAX,
                )?;
                id = next_id;
                data = next_data;
            }
            _ => return Err(WireError::DecodeError),
        }
    }
}

/// The request's own facts, or none for a request without facts.
fn fields_of<'a>(request: &'a TrezorUiEnum<'a>) -> &'a [WireField<'a>] {
    match request {
        TrezorUiEnum::Review(m) => m.fields.as_slice(),
        TrezorUiEnum::Danger(m) | TrezorUiEnum::Details(m) => m.fields.as_slice(),
        TrezorUiEnum::VerifyAddress(_) | TrezorUiEnum::VerifyPubkey(_) | TrezorUiEnum::Done(_) => {
            &[]
        }
    }
}

/// The request's extras, or none for a request without extras.
fn extras_of<'a>(request: &'a TrezorUiEnum<'a>) -> &'a [WireExtra<'a>] {
    match request {
        TrezorUiEnum::Review(m) => m.extras.as_slice(),
        _ => &[],
    }
}

/// The request as it crosses the wire, with the emptied facts it borrows.
fn crossing<'a>(
    request: &TrezorUiEnum<'a>,
    fields: &'a [WireField<'a>],
    extras: &'a [WireExtra<'a>],
) -> TrezorUiEnum<'a> {
    match request {
        TrezorUiEnum::Review(m) => TrezorUiEnum::Review(ReviewRequest {
            fields: Slice::new(fields),
            extras: Slice::new(extras),
            ..*m
        }),
        TrezorUiEnum::Danger(m) => TrezorUiEnum::Danger(FieldsRequest {
            fields: Slice::new(fields),
            ..*m
        }),
        TrezorUiEnum::Details(m) => TrezorUiEnum::Details(FieldsRequest {
            fields: Slice::new(fields),
            ..*m
        }),
        TrezorUiEnum::VerifyAddress(_) | TrezorUiEnum::VerifyPubkey(_) | TrezorUiEnum::Done(_) => {
            *request
        }
    }
}

/// `fields` with every `Data` value emptied and its length kept.
fn emptied<'a>(fields: &[WireField<'a>]) -> Vec<WireField<'a>> {
    fields
        .iter()
        .map(|field| {
            if field.kind == FieldKind::Data {
                WireField {
                    value: Slice::new(&[]),
                    ..*field
                }
            } else {
                *field
            }
        })
        .collect()
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
