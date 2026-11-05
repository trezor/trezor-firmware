use super::component::{ButtonDetails, ButtonPage, MenuNav, ScrollableFrame};
use super::{theme, UICaesar};
use crate::maybe_trace::MaybeTrace;
use crate::micropython::gc::Gc;
use crate::micropython::Error;
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::button_request::{ButtonRequest, ButtonRequestCode};
use crate::ui::component::text::paragraphs::{
    Paragraph, ParagraphSource as _, ParagraphVecShort, VecExt,
};
use crate::ui::component::{ButtonRequestExt as _, Component, Paginate};
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

/// Every screen is one scrollable button page on this model: the content, the
/// left button opening the menu or, without one, cancelling, and the verb on
/// the right, held when `hold`.
fn button_page<T: Component + Paginate + MaybeTrace + 'static>(
    title: TString<'static>,
    content: T,
    verb: TString<'static>,
    hold: bool,
    menu: bool,
    br: Option<ButtonRequest>,
) -> Result<Gc<LayoutObj>, Error> {
    let mut confirm = ButtonDetails::text(verb);
    if hold {
        confirm = confirm.with_default_duration();
    }
    let page = ButtonPage::new(content, theme::BG)
        .with_confirm_btn(Some(confirm))
        .with_menu_nav(if menu { MenuNav::Menu } else { MenuNav::Close });
    let frame = ScrollableFrame::new(page).with_title(title);
    match br {
        Some(br) => LayoutObj::new_root(RootComponent::new(frame.one_button_request(br))),
        None => LayoutObj::new_root(RootComponent::new(frame)),
    }
}

/// A value of the person's own, with its account and path, to confirm.
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
    button_page(
        title,
        paragraphs.into_paragraphs(),
        TR::buttons__confirm.into(),
        false,
        false,
        Some(br),
    )
}

impl ModUI for UICaesar {
    fn review(
        title: TString<'static>,
        fields: Fields,
        verb: Option<TString<'static>>,
        hold: bool,
        menu: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let verb = verb.unwrap_or(if hold {
            TR::buttons__hold_to_confirm.into()
        } else {
            TR::buttons__confirm.into()
        });
        let paragraphs = fields.paragraphs(&FIELD_STYLES).into_paragraphs();
        button_page(title, paragraphs, verb, hold, menu, None)
    }

    fn extra(title: TString<'static>, fields: Fields) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = fields.paragraphs(&FIELD_STYLES).into_paragraphs();
        button_page(
            title,
            paragraphs,
            TR::buttons__continue.into(),
            false,
            false,
            None,
        )
    }

    fn danger(title: TString<'static>, fields: Fields) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = fields.paragraphs(&FIELD_STYLES).into_paragraphs();
        button_page(
            title,
            paragraphs,
            TR::buttons__continue_anyway.into(),
            false,
            false,
            None,
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
        // This model has no success screen: the info screen says the same and
        // goes away after the same time.
        Self::show_info(TR::words__title_done.into(), text, None, time_ms, false)
    }
}
