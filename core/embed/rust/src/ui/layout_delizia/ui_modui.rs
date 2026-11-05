use trezor_app_sdk::structs::FieldKind;

use super::flow::{
    self, new_confirm_action_simple, ConfirmActionExtra, ConfirmActionMenuStrings,
    ConfirmActionOptions, ConfirmActionStrings,
};
use super::{theme, UIDelizia};
use crate::micropython::gc::Gc;
use crate::micropython::list::List;
use crate::micropython::Error;
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::button_request::ButtonRequestCode;
use crate::ui::component::text::paragraphs::ParagraphSource as _;
use crate::ui::layout::obj::LayoutObj;
use crate::ui::ui_firmware::FirmwareUI;
use crate::ui::ui_modui::{FieldStyles, Fields, ModUI, Shape};

/// `amount` matches the summary's amount, `address` keeps the chunking this
/// model gives addresses, `data` is mono without chunking, a `note` reads like
/// the descriptions around it, and a `warning` is the caution row.
static FIELD_STYLES: FieldStyles = FieldStyles {
    label: &theme::PROPS_KEY_FONT,
    text: &theme::TEXT_NORMAL,
    amount: &theme::TEXT_MONO_GREY_LIGHT,
    address: &theme::TEXT_MONO_ADDRESS_CHUNKS,
    data: &theme::TEXT_MONO_DATA,
    note: &theme::TEXT_MAIN_GREY_LIGHT,
    warning: &theme::TEXT_WARNING,
    label_spacing: theme::PROP_INNER_SPACING,
    field_spacing: theme::PROPS_SPACING,
};

impl ModUI for UIDelizia {
    fn review(
        title: TString<'static>,
        fields: Fields,
        verb: Option<TString<'static>>,
        hold: bool,
        menu: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let cancel = !menu;
        match fields.shape()? {
            Shape::Sentences(text) => LayoutObj::new_root(Self::confirm_action(
                title,
                Some(text),
                None,
                None,
                verb,
                cancel,
                None,
                hold,
                false,
                false,
                false,
                None,
                menu,
            )?),
            Shape::Value {
                kind,
                value,
                description,
            } => LayoutObj::new_root(Self::confirm_value(
                title,
                value,
                description,
                kind == FieldKind::Data,
                None,
                None,
                verb,
                None,
                false,
                hold,
                kind == FieldKind::Address,
                kind == FieldKind::Data,
                false,
                cancel,
                false,
                None,
                menu,
            )?),
            Shape::List => LayoutObj::new_root(new_confirm_action_simple(
                fields.paragraphs(&FIELD_STYLES).into_paragraphs(),
                if menu {
                    ConfirmActionExtra::ExternalMenu
                } else {
                    ConfirmActionExtra::Menu(ConfirmActionMenuStrings::new())
                },
                ConfirmActionStrings::new(title, None, None, hold.then_some(title)),
                ConfirmActionOptions::new().with_hold(hold),
            )?),
        }
    }

    fn extra(title: TString<'static>, fields: Fields) -> Result<Gc<LayoutObj>, Error> {
        LayoutObj::new_root(new_confirm_action_simple(
            fields.paragraphs(&FIELD_STYLES).into_paragraphs(),
            ConfirmActionExtra::Cancel,
            ConfirmActionStrings::new(title, None, None, None),
            ConfirmActionOptions::new(),
        )?)
    }

    fn danger(title: TString<'static>, fields: Fields) -> Result<Gc<LayoutObj>, Error> {
        LayoutObj::new_root(flow::show_danger::new_show_danger_fields(
            title,
            fields.paragraphs(&FIELD_STYLES),
        )?)
    }

    fn verify_address(
        address: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        br_name: TString<'static>,
    ) -> Result<Gc<LayoutObj>, Error> {
        LayoutObj::new_root(Self::flow_get_address(
            address,
            TR::words__receive.into(),
            None,
            Some(TString::empty()),
            None,
            true,
            address,
            true,
            account,
            path,
            List::alloc(&[])?.into(),
            ButtonRequestCode::Address as u16,
            br_name,
        )?)
    }

    fn verify_pubkey(
        pubkey: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        br_name: TString<'static>,
    ) -> Result<Gc<LayoutObj>, Error> {
        LayoutObj::new_root(Self::flow_get_pubkey(
            pubkey,
            TR::address__public_key.into(),
            None,
            None,
            pubkey,
            account,
            path,
            ButtonRequestCode::PublicKey as u16,
            br_name,
        )?)
    }

    fn done(text: TString<'static>, time_ms: u32) -> Result<Gc<LayoutObj>, Error> {
        Self::show_success(
            TR::words__title_done.into(),
            TR::instructions__continue_in_app.into(),
            text,
            false,
            time_ms,
        )
    }
}
