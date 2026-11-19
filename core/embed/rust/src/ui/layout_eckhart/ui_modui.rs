use super::component::Button;
use super::firmware::{ActionBar, Header, TextScreen, TextScreenMsg};
use super::{flow, fonts, theme, UIEckhart};
use crate::micropython::gc::Gc;
use crate::micropython::list::List;
use crate::micropython::Error;
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::button_request::ButtonRequestCode;
use crate::ui::component::text::paragraphs::ParagraphSource as _;
use crate::ui::component::text::TextStyle;
use crate::ui::component::ComponentExt as _;
use crate::ui::flow::FlowMsg;
use crate::ui::geometry::LinearPlacement;
use crate::ui::layout::obj::LayoutObj;
use crate::ui::ui_firmware::FirmwareUI;
use crate::ui::ui_modui::{FieldStyles, Fields, ModUI};

/// A warning inside a list of facts: a caution row, in the orange this model
/// gives its caution hints.
const TEXT_WARNING: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_REGULAR_22,
    theme::ORANGE,
    theme::BG,
    theme::ORANGE,
    theme::ORANGE,
)
.with_line_spacing(-4);

/// `amount` is the style the summary draws its amount with, `address` keeps
/// the chunking this model gives addresses, `data` is mono without chunking,
/// and a `note` is plain text: a label's style would make it read as one.
static FIELD_STYLES: FieldStyles = FieldStyles {
    label: &theme::TEXT_SMALL_LIGHT,
    text: &theme::TEXT_REGULAR,
    amount: &theme::TEXT_MONO_MEDIUM_LIGHT,
    address: &theme::TEXT_MONO_ADDRESS_CHUNKS,
    data: &theme::TEXT_MONO_MEDIUM_LIGHT_DATA,
    note: &theme::TEXT_REGULAR,
    warning: &TEXT_WARNING,
    label_spacing: theme::PROP_INNER_SPACING,
    field_spacing: theme::PROPS_SPACING,
};

impl ModUI for UIEckhart {
    fn review(
        title: TString<'static>,
        fields: Fields,
        verb: Option<TString<'static>>,
        hold: bool,
        menu: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        // One screen for every review, whatever it holds. The way out lives in
        // the menu: the driver's when the review has one, the screen's own
        // otherwise. A `Data` field's pages are counted in the hint.
        let paragraphs = fields
            .paragraphs(&FIELD_STYLES)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());
        LayoutObj::new_root(flow::new_confirm_with_menu(
            title,
            None,
            paragraphs,
            None,
            verb,
            hold,
            fields.has_data(),
            None,
            None,
            menu,
        )?)
    }

    fn extra(title: TString<'static>, fields: Fields) -> Result<Gc<LayoutObj>, Error> {
        // One fact per screen, so the bar offers the way forward; the header's
        // close button leaves the extra at any fact.
        let paragraphs = fields
            .paragraphs(&FIELD_STYLES)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());
        // Continue moves to the extra's next page, as the other models' extras do.
        let screen = TextScreen::new(paragraphs)
            .with_header(Header::new(title).with_close_button())
            .with_action_bar(ActionBar::new_single(Button::with_text(
                TR::buttons__continue.into(),
            )))
            .map(|msg| match msg {
                TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
                TextScreenMsg::Menu => Some(FlowMsg::Info),
                TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            });
        LayoutObj::new_root(flow::util::single_page(screen)?)
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
