use heapless::Vec;

use crate::{
    error::{self},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs},
            ComponentExt, MsgMap,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Alignment, Direction, LinearPlacement, Offset},
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, Hint, TextScreen, TextScreenMsg, VerticalMenu, VerticalMenuScreen,
        VerticalMenuScreenMsg,
    },
    theme,
};

const MENU_ITEM_CANCEL: usize = 0;
const MENU_ITEM_EXTRA_INFO: usize = 1;
const MENU_ITEM_ACCOUNT_INFO: usize = 2;

const TIMEOUT_MS: u32 = 2000;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmSummary {
    Summary,
    Menu,
    ExtraInfo,
    AccountInfo,
    Cancel,
    Cancelled,
}

impl FlowController for ConfirmSummary {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Summary, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Summary, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => Self::Cancel.goto(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_EXTRA_INFO)) => Self::ExtraInfo.goto(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => Self::AccountInfo.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Summary.goto(),
            (_, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Cancel, FlowMsg::Confirmed) => Self::Cancelled.goto(),
            (Self::Cancelled, _) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

fn content_menu_info(
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    paragraphs: Option<ParagraphVecShort<'static>>,
) -> MsgMap<
    TextScreen<Paragraphs<ParagraphVecShort<'static>>>,
    impl Fn(TextScreenMsg) -> Option<FlowMsg>,
> {
    TextScreen::new(
        paragraphs
            .map_or_else(ParagraphVecShort::new, |p| p)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical())
            .with_spacing(12),
    )
    .with_header(Header::new(title).with_close_button())
    .with_subtitle(subtitle.unwrap_or(TString::empty()))
    .map(|_| Some(FlowMsg::Cancelled))
}

#[allow(clippy::too_many_arguments)]
pub fn new_confirm_summary(
    title: TString<'static>,
    amount: TString<'static>,
    amount_label: TString<'static>,
    fee: TString<'static>,
    fee_label: TString<'static>,
    account_paragraphs: Option<ParagraphVecShort<'static>>,
    extra_title: Option<TString<'static>>,
    extra_paragraphs: Option<ParagraphVecShort<'static>>,
    verb_cancel: Option<TString<'static>>,
) -> Result<SwipeFlow, error::Error> {
    // Summary
    let summary_paragraphs = ParagraphVecShort::from_iter([
        Paragraph::new(&theme::TEXT_SMALL_LIGHT, amount_label),
        Paragraph::new(&theme::TEXT_MONO_MEDIUM_LIGHT, amount),
        Paragraph::new(&theme::TEXT_SMALL_LIGHT, fee_label),
        Paragraph::new(&theme::TEXT_MONO_MEDIUM_LIGHT, fee),
    ]);

    let content_summary = TextScreen::new(
        summary_paragraphs
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical())
            .with_spacing(12),
    )
    .with_header(Header::new(title).with_menu_button())
    .with_action_bar(ActionBar::new_single(
        Button::with_text(TR::instructions__hold_to_sign.into())
            .with_long_press(theme::CONFIRM_HOLD_DURATION)
            .styled(theme::button_confirm()),
    ))
    .with_hint(Hint::new_instruction(
        TR::send__send_in_the_app,
        Some(theme::ICON_INFO),
    ))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        TextScreenMsg::Menu => Some(FlowMsg::Info),
    });

    // Menu
    let mut menu = VerticalMenu::empty();
    let mut menu_items = Vec::<usize, 3>::new();

    if account_paragraphs.is_some() {
        menu = menu.item(
            Button::with_text(TR::address_details__account_info.into())
                .styled(theme::menu_item_title())
                .with_text_align(Alignment::Start)
                .with_content_offset(Offset::x(12)),
        );
        unwrap!(menu_items.push(MENU_ITEM_ACCOUNT_INFO));
    }
    if extra_paragraphs.is_some() {
        menu = menu.item(
            Button::with_text(extra_title.unwrap_or(TR::buttons__more_info.into()))
                .styled(theme::menu_item_title())
                .with_text_align(Alignment::Start)
                .with_content_offset(Offset::x(12)),
        );
        unwrap!(menu_items.push(MENU_ITEM_EXTRA_INFO));
    }
    menu = menu.item(
        Button::with_text(verb_cancel.unwrap_or(TR::buttons__cancel.into()))
            .styled(theme::menu_item_title_orange())
            .with_text_align(Alignment::Start)
            .with_content_offset(Offset::x(12)),
    );
    unwrap!(menu_items.push(MENU_ITEM_CANCEL));
    let content_menu = VerticalMenuScreen::new(menu)
        .with_header(Header::new(title).with_close_button())
        .map(move |msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => {
                let selected_item = menu_items[i];
                Some(FlowMsg::Choice(selected_item))
            }
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    // ExtraInfo
    let content_extra = content_menu_info(
        extra_title.unwrap_or(TR::buttons__more_info.into()),
        None,
        extra_paragraphs,
    );

    // AccountInfo
    let content_account = content_menu_info(
        TR::address_details__account_info.into(),
        Some(TR::send__send_from.into()),
        account_paragraphs,
    );

    // Cancel
    let content_cancel = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, TR::send__cancel_sign)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(TR::words__send.into()))
    .with_action_bar(ActionBar::new_double(
        Button::with_icon(theme::ICON_CHEVRON_LEFT),
        Button::with_text(TR::buttons__cancel.into()).styled(theme::button_cancel()),
    ))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        _ => None,
    });

    // Cancelled
    let content_cancelled = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, TR::send__sign_cancelled)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(TR::words__title_done.into()).with_icon(theme::ICON_DONE, theme::GREY))
    .with_action_bar(ActionBar::new_timeout(
        Button::with_text(TR::instructions__continue_in_app.into()),
        TIMEOUT_MS,
    ))
    .map(|_| Some(FlowMsg::Confirmed));

    let mut res = SwipeFlow::new(&ConfirmSummary::Summary)?;
    res.add_page(&ConfirmSummary::Summary, content_summary)?
        .add_page(&ConfirmSummary::Menu, content_menu)?
        .add_page(&ConfirmSummary::ExtraInfo, content_extra)?
        .add_page(&ConfirmSummary::AccountInfo, content_account)?
        .add_page(&ConfirmSummary::Cancel, content_cancel)?
        .add_page(&ConfirmSummary::Cancelled, content_cancelled)?;

    Ok(res)
}
