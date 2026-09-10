//! Implements [`trezor_app_sdk::traits::ui`]'s `UiV1` on top of
//! [`crate::wire::ipc_call`]. Each method converts its stabby-safe mirror
//! argument into the matching `trezor_app_sdk::structs` (wire-format) enum
//! variant, sends it to Core's UI/progress service, and converts the
//! response back.

use rkyv::rancor::Failure;
use rkyv::to_bytes;
use stabby::option::Option as StabbyOption;
use stabby::slice::Slice;
use trezor_app_sdk::structs::{self, TrezorProgressEnum, TrezorUiEnum, TrezorUiResult as WireTrezorUiResult};
use trezor_app_sdk::traits::ui::{
    ConfirmAction, ConfirmProperties, ConfirmSummary, ConfirmTrade, ConfirmValue,
    ConfirmValueIntro, ConfirmWithInfo, Property, RequestNumber, SelectMenu, ShowAddress,
    ShowDanger, ShowInfoWithCancel, ShowMismatch, ShowProperties, ShowPublicKey, ShowSuccess,
    ShowWarning, StrExt, TrezorUiResult, UiV1, as_opt_str,
};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::WireError;

use crate::wire::{CoreIpcService, ipc_call};

fn opt_str(bytes: StabbyOption<Slice<'_, u8>>) -> Option<structs::StrSlice<'_>> {
    as_opt_str(bytes).map(Into::into)
}

fn to_properties<'a>(props: &[Property<'a>], out: &mut alloc::vec::Vec<structs::Property<'a>>) {
    out.extend(
        props
            .iter()
            .map(|p| structs::Property::new(p.key.as_str(), p.value.as_str(), p.mono)),
    );
}

fn to_str_exts<'a>(items: &[StrExt<'a>], out: &mut alloc::vec::Vec<structs::StrExt<'a>>) {
    out.extend(
        items
            .iter()
            .map(|s| structs::StrExt::new(s.key.as_str(), s.mono)),
    );
}

/// Sends `value` to Core's UI service and deserializes the (owned) result.
fn ipc_ui_call(value: &TrezorUiEnum) -> Result<WireTrezorUiResult, WireError> {
    let bytes = to_bytes::<Failure>(value).map_err(|_| WireError::DecodeError)?;
    let (_id, data) = ipc_call(CoreIpcService::Ui.into(), 0, &bytes, TIMEOUT_MAX)?;
    let archived = rkyv::access::<rkyv::Archived<WireTrezorUiResult>, Failure>(data)
        .map_err(|_| WireError::DecodeError)?;
    rkyv::api::low::deserialize::<WireTrezorUiResult, Failure>(archived)
        .map_err(|_| WireError::DecodeError)
}

fn to_mirror(result: WireTrezorUiResult) -> TrezorUiResult {
    match result {
        WireTrezorUiResult::Confirmed => TrezorUiResult::Confirmed,
        WireTrezorUiResult::Back => TrezorUiResult::Back,
        WireTrezorUiResult::Cancelled => TrezorUiResult::Cancelled,
        WireTrezorUiResult::Info => TrezorUiResult::Info,
        WireTrezorUiResult::Integer(n) => TrezorUiResult::Integer(n),
    }
}

/// Send a UI call and pass the result through unchanged.
fn ui_call(value: &TrezorUiEnum) -> Result<TrezorUiResult, WireError> {
    ipc_ui_call(value).map(to_mirror)
}

/// Send a UI call and normalize the result to a plain confirmation: anything
/// but [`WireTrezorUiResult::Confirmed`] becomes [`TrezorUiResult::Cancelled`].
fn ui_call_confirm(value: &TrezorUiEnum) -> Result<TrezorUiResult, WireError> {
    match ipc_ui_call(value)? {
        WireTrezorUiResult::Confirmed => Ok(TrezorUiResult::Confirmed),
        _ => Ok(TrezorUiResult::Cancelled),
    }
}

/// Send a UI call that doesn't expect a meaningful response.
fn ui_call_void(value: &TrezorUiEnum) -> Result<(), WireError> {
    ipc_ui_call(value)?;
    Ok(())
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
    extern "C" fn confirm_value<'a>(
        &self,
        value: ConfirmValue<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        ui_call(&TrezorUiEnum::ConfirmValue(structs::ConfirmValue {
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
            footer: as_opt_str(value.footer_text).map(|t| (t.into(), value.footer_bold)),
        }))
        .into()
    }

    extern "C" fn confirm_value_intro<'a>(
        &self,
        value: ConfirmValueIntro<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        ui_call(&TrezorUiEnum::ConfirmValueIntro(
            structs::ConfirmValueIntro {
                title: value.title.as_str().into(),
                value: value.value.as_str().into(),
                subtitle: opt_str(value.subtitle),
                verb: opt_str(value.verb),
                verb_cancel: opt_str(value.verb_cancel),
                verb_view_all: opt_str(value.verb_view_all),
                hold: value.hold,
                chunkify: value.chunkify,
                br_name: opt_str(value.br_name),
                br_code: value.br_code,
            },
        ))
        .into()
    }

    extern "C" fn confirm_summary<'a>(
        &self,
        value: ConfirmSummary<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        let mut account_items = alloc::vec::Vec::new();
        let mut extra_items = alloc::vec::Vec::new();
        if let core::option::Option::Some(items) =
            core::option::Option::<Slice<'a, Property<'a>>>::from(value.account_items)
        {
            to_properties(items.as_slice(), &mut account_items);
        }
        if let core::option::Option::Some(items) =
            core::option::Option::<Slice<'a, Property<'a>>>::from(value.extra_items)
        {
            to_properties(items.as_slice(), &mut extra_items);
        }
        ui_call(&TrezorUiEnum::ConfirmSummary(structs::ConfirmSummary {
            title: value.title.as_str().into(),
            amount: opt_str(value.amount),
            amount_label: opt_str(value.amount_label),
            fee: value.fee.as_str().into(),
            fee_label: value.fee_label.as_str().into(),
            account_title: opt_str(value.account_title),
            account_items: if account_items.is_empty() {
                None
            } else {
                Some(account_items.as_slice().into())
            },
            extra_title: opt_str(value.extra_title),
            extra_items: if extra_items.is_empty() {
                None
            } else {
                Some(extra_items.as_slice().into())
            },
            back_button: value.back_button,
            br_name: opt_str(value.br_name),
            br_code: value.br_code,
        }))
        .into()
    }

    extern "C" fn confirm_action<'a>(
        &self,
        value: ConfirmAction<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        ui_call(&TrezorUiEnum::ConfirmAction(structs::ConfirmAction {
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
        }))
        .into()
    }

    extern "C" fn select_menu<'a>(
        &self,
        value: SelectMenu<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        let items: alloc::vec::Vec<structs::StrSlice> =
            value.items.as_slice().iter().map(|s| s.as_str().into()).collect();
        ui_call(&TrezorUiEnum::SelectMenu(structs::SelectMenu {
            items: items.as_slice().into(),
            cancel: opt_str(value.cancel),
            br_code: value.br_code,
        }))
        .into()
    }

    extern "C" fn confirm_properties<'a>(
        &self,
        value: ConfirmProperties<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        let mut props = alloc::vec::Vec::new();
        to_properties(value.props.as_slice(), &mut props);
        ui_call(&TrezorUiEnum::ConfirmProperties(
            structs::ConfirmProperties {
                title: value.title.as_str().into(),
                props: props.as_slice().into(),
                subtitle: opt_str(value.subtitle),
                verb: opt_str(value.verb),
                hold: value.hold,
                br_name: opt_str(value.br_name),
                br_code: value.br_code,
            },
        ))
        .into()
    }

    extern "C" fn show_properties<'a>(
        &self,
        value: ShowProperties<'a>,
    ) -> FastResult<(), WireError> {
        let mut props = alloc::vec::Vec::new();
        to_properties(value.props.as_slice(), &mut props);
        ui_call_void(&TrezorUiEnum::ShowProperties(structs::ShowProperties {
            title: value.title.as_str().into(),
            props: props.as_slice().into(),
            subtitle: opt_str(value.subtitle),
            br_name: opt_str(value.br_name),
            br_code: value.br_code,
        }))
        .into()
    }

    extern "C" fn show_warning<'a>(&self, value: ShowWarning<'a>) -> FastResult<(), WireError> {
        ui_call_void(&TrezorUiEnum::ShowWarning(structs::ShowWarning {
            title: value.title.as_str().into(),
            content: value.content.as_str().into(),
            verb: value.verb.as_str().into(),
            br_name: opt_str(value.br_name),
            br_code: value.br_code,
            allow_cancel: value.allow_cancel,
            danger: value.danger,
        }))
        .into()
    }

    extern "C" fn show_info_with_cancel<'a>(
        &self,
        value: ShowInfoWithCancel<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        let mut items = alloc::vec::Vec::new();
        to_properties(value.items.as_slice(), &mut items);
        ui_call_confirm(&TrezorUiEnum::ShowInfoWithCancel(
            structs::ShowInfoWithCancel {
                title: value.title.as_str().into(),
                items: items.as_slice().into(),
                chunkify: value.chunkify,
                br_name: opt_str(value.br_name),
                br_code: value.br_code,
            },
        ))
        .into()
    }

    extern "C" fn show_mismatch<'a>(
        &self,
        value: ShowMismatch<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        ui_call_confirm(&TrezorUiEnum::ShowMismatch(structs::ShowMismatch {
            title: value.title.as_str().into(),
            br_code: value.br_code,
        }))
        .into()
    }

    extern "C" fn confirm_trade<'a>(
        &self,
        value: ConfirmTrade<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        ui_call(&TrezorUiEnum::ConfirmTrade(structs::ConfirmTrade {
            title: value.title.as_str().into(),
            subtitle: value.subtitle.as_str().into(),
            buy: value.buy.as_str().into(),
            sell: opt_str(value.sell),
            back_button: value.back_button,
            br_name: opt_str(value.br_name),
            br_code: value.br_code,
        }))
        .into()
    }

    extern "C" fn show_danger<'a>(
        &self,
        value: ShowDanger<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        ui_call_confirm(&TrezorUiEnum::ShowDanger(structs::ShowDanger {
            title: value.title.as_str().into(),
            content: value.content.as_str().into(),
            br_name: opt_str(value.br_name),
            br_code: value.br_code,
            verb_cancel: opt_str(value.verb_cancel),
            menu_title: opt_str(value.menu_title),
        }))
        .into()
    }

    extern "C" fn show_success<'a>(&self, value: ShowSuccess<'a>) -> FastResult<(), WireError> {
        ui_call_void(&TrezorUiEnum::ShowSuccess(structs::ShowSuccess {
            title: value.title.as_str().into(),
            content: value.content.as_str().into(),
            button: value.button.as_str().into(),
            duration_ms: value.duration_ms.into(),
            br_name: opt_str(value.br_name),
            br_code: value.br_code,
        }))
        .into()
    }

    extern "C" fn request_number<'a>(
        &self,
        value: RequestNumber<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        match ui_call(&TrezorUiEnum::RequestNumber(structs::RequestNumber {
            title: value.title.as_str().into(),
            content: value.content.as_str().into(),
            initial: value.initial,
            min: value.min,
            max: value.max,
            br_code: value.br_code,
        })) {
            Ok(result @ TrezorUiResult::Integer(_)) => Ok(result),
            Ok(_) => Ok(TrezorUiResult::Cancelled),
            Err(e) => Err(e),
        }
        .into()
    }

    extern "C" fn show_public_key<'a>(
        &self,
        value: ShowPublicKey<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        ui_call(&TrezorUiEnum::ShowPublicKey(structs::ShowPublicKey {
            pubkey: value.pubkey.as_str().into(),
            title: value.title.as_str().into(),
            account: opt_str(value.account),
            path: opt_str(value.path),
            warning: opt_str(value.warning),
            br_name: value.br_name.as_str().into(),
            br_code: value.br_code,
        }))
        .into()
    }

    extern "C" fn confirm_with_info<'a>(
        &self,
        value: ConfirmWithInfo<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        let mut items = alloc::vec::Vec::new();
        to_str_exts(value.items.as_slice(), &mut items);
        ui_call(&TrezorUiEnum::ConfirmWithInfo(structs::ConfirmWithInfo {
            title: value.title.as_str().into(),
            subtitle: opt_str(value.subtitle),
            items: items.as_slice().into(),
            verb: value.verb.as_str().into(),
            verb_info: opt_str(value.verb_info),
            br_name: opt_str(value.br_name),
            br_code: value.br_code,
        }))
        .into()
    }

    extern "C" fn show_address<'a>(
        &self,
        value: ShowAddress<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        let mut xpubs = alloc::vec::Vec::new();
        to_properties(value.xpubs.as_slice(), &mut xpubs);
        ui_call(&TrezorUiEnum::ShowAddress(structs::ShowAddress {
            address: value.address.as_str().into(),
            address_qr: value.address_qr.as_str().into(),
            title: opt_str(value.title),
            subtitle: opt_str(value.subtitle),
            account: opt_str(value.account),
            path: opt_str(value.path),
            xpubs: xpubs.as_slice().into(),
            chunkify: value.chunkify,
            br_code: value.br_code,
            case_sensitive: value.case_sensitive,
        }))
        .into()
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
