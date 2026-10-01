//! Implements [`trezor_app_sdk::traits::ui`]'s `UiV1` on top of
//! [`crate::wire::ipc_call`]. Each method converts its stabby-safe mirror
//! argument into the matching `trezor_app_sdk::structs` (wire-format) enum
//! variant, sends it to Core's UI/progress service, and converts the
//! response back.
//!
//! The op and the layout handle ride in the IPC message id;
//! `apps/extapp/run.py` unpacks them.

use rkyv::rancor::Failure;
use rkyv::to_bytes;
use stabby::option::Option as StabbyOption;
use stabby::slice::Slice;
use trezor_app_sdk::structs::{self, TrezorProgressEnum, TrezorUiEnum};
use trezor_app_sdk::traits::ui::{
    ConfirmAction, ConfirmProperties, ConfirmSummary, ConfirmValue, HANDLE_BITS, Property,
    SelectMenu, Severity, ShowNotice, ShowProperties, UiReply, UiV1, as_opt_str,
};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::WireError;

use crate::wire::{CoreIpcService, ipc_call};

/// Drop the layout held under the handle. Core-side only: apps reach it
/// through [`UiV1::close`].
const OP_CLOSE: u16 = 3;

type Properties<'a> = alloc::vec::Vec<structs::Property<'a>>;

fn opt_str(bytes: StabbyOption<Slice<'_, u8>>) -> Option<structs::StrSlice<'_>> {
    as_opt_str(bytes).map(Into::into)
}

fn to_properties<'a>(props: &[Property<'a>]) -> Properties<'a> {
    props
        .iter()
        .map(|p| structs::Property::new(p.key.as_str(), p.value.as_str(), p.mono))
        .collect()
}

fn opt_properties<'a>(props: StabbyOption<Slice<'a, Property<'a>>>) -> Option<Properties<'a>> {
    Option::<Slice<'a, Property<'a>>>::from(props).map(|p| to_properties(p.as_slice()))
}

/// Packs an operation and a layout handle into the 16-bit IPC message id.
fn message_id(op: u16, handle: u16) -> u16 {
    (op << HANDLE_BITS) | (handle & ((1 << HANDLE_BITS) - 1))
}

/// Sends one UI message to Core and returns the raw reply.
fn ipc_ui_raw(op: u16, handle: u16, payload: &[u8]) -> Result<structs::UiReply, WireError> {
    let id = message_id(op, handle);
    let (_id, data) = ipc_call(CoreIpcService::Ui.into(), id, payload, TIMEOUT_MAX)?;
    let archived = rkyv::access::<rkyv::Archived<structs::UiReply>, Failure>(&data)
        .map_err(|_| WireError::DecodeError)?;
    rkyv::api::low::deserialize::<structs::UiReply, Failure>(archived)
        .map_err(|_| WireError::DecodeError)
}

/// Sends `value` to Core's UI service and converts the reply to its mirror.
fn ui_call(op: u16, handle: u16, value: &TrezorUiEnum) -> FastResult<UiReply, WireError> {
    let result = to_bytes::<Failure>(value)
        .map_err(|_| WireError::DecodeError)
        .and_then(|bytes| ipc_ui_raw(op, handle, &bytes))
        .map(|reply| match reply {
            structs::UiReply::Confirmed => UiReply::Confirmed,
            structs::UiReply::Cancelled => UiReply::Cancelled,
            structs::UiReply::WantsMore => UiReply::WantsMore,
            structs::UiReply::Choice(i) => UiReply::Choice(i),
            structs::UiReply::Forward => UiReply::Forward,
            structs::UiReply::Backward => UiReply::Backward,
            structs::UiReply::ConfirmedAll => UiReply::ConfirmedAll,
        });
    result.into()
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
        ui_call(
            op,
            handle,
            &TrezorUiEnum::ConfirmAction(structs::ConfirmAction {
                title: value.title.as_str().into(),
                action: value.action.as_str().into(),
                description: opt_str(value.description),
                subtitle: opt_str(value.subtitle),
                hold: value.hold,
                cancel: value.cancel,
                verb: opt_str(value.verb),
                br_name: opt_str(value.br_name),
                br_code: value.br_code,
                external_menu: value.external_menu,
            }),
        )
    }

    extern "C" fn confirm_value<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmValue<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(
            op,
            handle,
            &TrezorUiEnum::ConfirmValue(structs::ConfirmValue {
                title: value.title.as_str().into(),
                value: value.value.as_str().into(),
                description: opt_str(value.description),
                is_data: value.is_data,
                subtitle: opt_str(value.subtitle),
                verb: opt_str(value.verb),
                info: value.info,
                hold: value.hold,
                chunkify: value.chunkify,
                page_counter: value.page_counter,
                cancel: value.cancel,
                br_name: opt_str(value.br_name),
                br_code: value.br_code,
                external_menu: value.external_menu,
                footer: opt_str(value.footer_text).map(|t| (t, value.footer_bold)),
            }),
        )
    }

    extern "C" fn confirm_summary<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmSummary<'a>,
    ) -> FastResult<UiReply, WireError> {
        let account_items = opt_properties(value.account_items);
        let extra_items = opt_properties(value.extra_items);
        ui_call(
            op,
            handle,
            &TrezorUiEnum::ConfirmSummary(structs::ConfirmSummary {
                title: value.title.as_str().into(),
                amount: opt_str(value.amount),
                amount_label: opt_str(value.amount_label),
                fee: value.fee.as_str().into(),
                fee_label: value.fee_label.as_str().into(),
                account_title: opt_str(value.account_title),
                account_items: account_items.as_deref().map(Into::into),
                extra_title: opt_str(value.extra_title),
                extra_items: extra_items.as_deref().map(Into::into),
                back_button: value.back_button,
                external_menu: value.external_menu,
                br_name: opt_str(value.br_name),
                br_code: value.br_code,
            }),
        )
    }

    extern "C" fn confirm_properties<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmProperties<'a>,
    ) -> FastResult<UiReply, WireError> {
        let props = to_properties(value.props.as_slice());
        ui_call(
            op,
            handle,
            &TrezorUiEnum::ConfirmProperties(structs::ConfirmProperties {
                title: value.title.as_str().into(),
                props: props.as_slice().into(),
                subtitle: opt_str(value.subtitle),
                verb: opt_str(value.verb),
                hold: value.hold,
                br_name: opt_str(value.br_name),
                br_code: value.br_code,
            }),
        )
    }

    extern "C" fn show_properties<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ShowProperties<'a>,
    ) -> FastResult<UiReply, WireError> {
        let props = to_properties(value.props.as_slice());
        ui_call(
            op,
            handle,
            &TrezorUiEnum::ShowProperties(structs::ShowProperties {
                title: value.title.as_str().into(),
                props: props.as_slice().into(),
                subtitle: opt_str(value.subtitle),
                br_name: opt_str(value.br_name),
                br_code: value.br_code,
            }),
        )
    }

    extern "C" fn show_notice<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ShowNotice<'a>,
    ) -> FastResult<UiReply, WireError> {
        ui_call(
            op,
            handle,
            &TrezorUiEnum::ShowNotice(structs::ShowNotice {
                severity: match value.severity {
                    Severity::Success => structs::Severity::Success,
                    Severity::Done => structs::Severity::Done,
                    Severity::Info => structs::Severity::Info,
                    Severity::Warning => structs::Severity::Warning,
                    Severity::Danger => structs::Severity::Danger,
                },
                title: value.title.as_str().into(),
                content: value.content.as_str().into(),
                external_menu: value.external_menu,
                br_name: opt_str(value.br_name),
                br_code: value.br_code,
            }),
        )
    }

    extern "C" fn select_menu<'a>(
        &self,
        op: u16,
        handle: u16,
        value: SelectMenu<'a>,
    ) -> FastResult<UiReply, WireError> {
        let items: alloc::vec::Vec<structs::StrSlice> = value
            .items
            .as_slice()
            .iter()
            .map(|s| s.as_str().into())
            .collect();
        ui_call(
            op,
            handle,
            &TrezorUiEnum::SelectMenu(structs::SelectMenu {
                items: items.as_slice().into(),
                cancel: opt_str(value.cancel),
                refusable: value.refusable,
                br_name: opt_str(value.br_name),
                br_code: value.br_code,
            }),
        )
    }

    extern "C" fn close(&self, handle: u16) -> FastResult<(), WireError> {
        ipc_ui_raw(OP_CLOSE, handle, &[]).map(|_| ()).into()
    }

    extern "C" fn init_progress<'a>(
        &self,
        description: StabbyOption<Slice<'a, u8>>,
        title: StabbyOption<Slice<'a, u8>>,
        indeterminate: bool,
        danger: bool,
    ) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::Init {
            description: opt_str(description),
            title: opt_str(title),
            indeterminate,
            danger,
        })
        .into()
    }

    extern "C" fn update_progress<'a>(
        &self,
        description: StabbyOption<Slice<'a, u8>>,
        value: u32,
    ) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::Update {
            description: opt_str(description),
            value,
        })
        .into()
    }

    extern "C" fn end_progress(&self) -> FastResult<(), WireError> {
        ipc_progress_call(&TrezorProgressEnum::End).into()
    }
}
