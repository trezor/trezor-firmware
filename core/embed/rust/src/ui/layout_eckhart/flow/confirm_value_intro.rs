use crate::{
    error,
    micropython::obj::Obj,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource},
            ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Direction, LinearPlacement},
        layout::util::StrOrBytes,
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, ShortMenuVec, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

const TIMEOUT_MS: u32 = 2000;

const MENU_ITEM_CANCEL: usize = 0;
const MENU_ITEM_VIEW_ALL: usize = 1;
const MENU_ITEM_EXTRA: usize = 2;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmValueIntro {
    Intro,
    Menu,
}

impl FlowController for ConfirmValueIntro {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            // special case for the "view all data" button
            (Self::Intro, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Info),
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_VIEW_ALL)) => self.return_msg(FlowMsg::Info),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_EXTRA)) => {
                self.return_msg(FlowMsg::Choice(MENU_ITEM_EXTRA))
            }
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.goto(),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::too_many_arguments)]
pub fn new_confirm_value_intro(
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    value: Obj,
    cancel_menu_label: Option<TString<'static>>,
    confirm_button_label: Option<TString<'static>>,
    extra_menu_label: Option<TString<'static>>,
    hold: bool,
    chunkify: bool,
) -> Result<SwipeFlow, error::Error> {
    let cancel_menu_label = cancel_menu_label.unwrap_or(TR::buttons__cancel.into());

    // Intro
    let mut confirm_button = Button::with_text(
        confirm_button_label.unwrap_or(TR::sign_message__confirm_without_review.into()),
    );
    if hold {
        confirm_button = confirm_button.with_long_press(theme::CONFIRM_HOLD_DURATION);
    }

    let value = if value != Obj::const_none() {
        unwrap!(value.try_into())
    } else {
        StrOrBytes::Str("".into())
    };

    let intro_style = if chunkify {
        &theme::TEXT_MONO_ADDRESS_CHUNKS
    } else {
        &theme::TEXT_MONO_ADDRESS
    };
    let content_intro = TextScreen::new(
        Paragraph::new(intro_style, value.as_str_offset(0))
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_page_limit(1)
    .with_header(Header::new(title).with_menu_button())
    .with_subtitle(subtitle.unwrap_or(TString::empty()))
    .with_action_bar(
        ActionBar::new_double(
            Button::with_text(TR::buttons__view_all_data.into()),
            confirm_button,
        )
        .with_left_short(false),
    )
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        // special case for the "view all data" button
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        TextScreenMsg::Menu => Some(FlowMsg::Info),
    });

    let mut menu_items = VerticalMenu::<ShortMenuVec>::empty().with_item(Button::new_menu_item(
        TR::buttons__view_all_data.into(),
        theme::menu_item_title(),
    ));
    if let Some(extra_menu_label) = extra_menu_label {
        menu_items = menu_items.with_item(Button::new_menu_item(
            extra_menu_label,
            theme::menu_item_title(),
        ));
    }
    menu_items = menu_items.with_item(Button::new_cancel_menu_item(cancel_menu_label));

    let content_menu = VerticalMenuScreen::new(menu_items)
        .with_header(Header::new(TString::empty()).with_close_button())
        .map(move |msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => match (i, extra_menu_label) {
                (0, _) => Some(FlowMsg::Choice(MENU_ITEM_VIEW_ALL)),
                (1, None) => Some(FlowMsg::Choice(MENU_ITEM_CANCEL)),
                (1, Some(_)) => Some(FlowMsg::Choice(MENU_ITEM_EXTRA)),
                (2, _) => Some(FlowMsg::Choice(MENU_ITEM_CANCEL)),
                _ => unreachable!(),
            },
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let mut res = SwipeFlow::new(&ConfirmValueIntro::Intro)?;
    res.add_page(&ConfirmValueIntro::Intro, content_intro)?
        .add_page(&ConfirmValueIntro::Menu, content_menu)?;
    Ok(res)
}
