use super::component::{ButtonPage, Frame};
use super::{theme, UIBolt};
use crate::micropython::gc::Gc;
use crate::micropython::Error;
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::button_request::{ButtonRequest, ButtonRequestCode};
use crate::ui::component::text::paragraphs::{
    Paragraph, ParagraphSource as _, ParagraphVecShort, VecExt,
};
use crate::ui::component::ButtonRequestExt as _;
use crate::ui::layout::obj::{LayoutObj, RootComponent};
use crate::ui::ui_firmware::FirmwareUI;
use crate::ui::ui_modui::{FieldStyles, Fields, ModUI};

/// This model has no styles of its own for the field kinds: what is compared
/// character by character is mono, everything else is the plain value font.
static FIELD_STYLES: FieldStyles = FieldStyles {
    label: &theme::PROPS_KEY_FONT,
    text: &theme::PROPS_VALUE_FONT,
    amount: &theme::PROPS_VALUE_FONT,
    address: &theme::PROPS_VALUE_MONO_FONT,
    data: &theme::PROPS_VALUE_MONO_FONT,
    note: &theme::PROPS_VALUE_FONT,
    warning: &theme::PROPS_VALUE_FONT,
    label_spacing: theme::PROP_INNER_SPACING,
    field_spacing: theme::PROPS_SPACING,
};

/// Every request is a list of facts on this model, with a cancel button and
/// the confirm button or a hold; a menu opens from the info button.
fn fields_page(
    title: TString<'static>,
    fields: Fields,
    verb: TString<'static>,
    hold: bool,
    menu: bool,
) -> Result<Gc<LayoutObj>, Error> {
    let paragraphs = fields.paragraphs(&FIELD_STYLES).into_paragraphs();
    let page = if hold {
        ButtonPage::new(paragraphs, theme::BG).with_hold()?
    } else {
        ButtonPage::new(paragraphs, theme::BG).with_cancel_confirm(None, Some(verb))
    };
    let mut frame = Frame::left_aligned(theme::label_title(), title, page);
    if menu {
        frame = frame.with_info_button();
    }
    LayoutObj::new_root(RootComponent::new(frame))
}

/// A value of the person's own, with its account and path, to confirm. The
/// screen sends its own ButtonRequest, as the other models' flows do.
fn verify_page(
    title: TString<'static>,
    value: TString<'static>,
    account: Option<TString<'static>>,
    path: Option<TString<'static>>,
    br: ButtonRequest,
) -> Result<Gc<LayoutObj>, Error> {
    let mut paragraphs = ParagraphVecShort::new();
    paragraphs.add(Paragraph::new(&theme::PROPS_VALUE_MONO_FONT, value));
    for text in [account, path].into_iter().flatten() {
        paragraphs.add(Paragraph::new(&theme::PROPS_VALUE_FONT, text));
    }
    let page = ButtonPage::new(paragraphs.into_paragraphs(), theme::BG)
        .with_cancel_confirm(None, Some(TR::buttons__confirm.into()));
    let frame = Frame::left_aligned(theme::label_title(), title, page);
    LayoutObj::new_root(RootComponent::new(frame.one_button_request(br)))
}

impl ModUI for UIBolt {
    fn review(
        title: TString<'static>,
        fields: Fields,
        verb: Option<TString<'static>>,
        hold: bool,
        menu: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let verb = verb.unwrap_or(TR::buttons__confirm.into());
        fields_page(title, fields, verb, hold, menu)
    }

    fn extra(title: TString<'static>, fields: Fields) -> Result<Gc<LayoutObj>, Error> {
        fields_page(title, fields, TR::buttons__continue.into(), false, false)
    }

    fn danger(title: TString<'static>, fields: Fields) -> Result<Gc<LayoutObj>, Error> {
        fields_page(
            title,
            fields,
            TR::buttons__continue_anyway.into(),
            false,
            false,
        )
    }

    fn verify_address(
        address: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        br_name: TString<'static>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let br = ButtonRequest::new(ButtonRequestCode::Address, br_name);
        verify_page(TR::words__receive.into(), address, account, path, br)
    }

    fn verify_pubkey(
        pubkey: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        br_name: TString<'static>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let br = ButtonRequest::new(ButtonRequestCode::PublicKey, br_name);
        verify_page(TR::address__public_key.into(), pubkey, account, path, br)
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
