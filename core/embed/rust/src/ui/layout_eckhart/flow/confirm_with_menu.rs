use crate::{
    error,
    maybe_trace::MaybeTrace,
    strutil::TString,
    translations::TR,
    ui::{
        component::ComponentExt,
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, AllowedTextContent, Header, ShortMenuVec, TextScreen, TextScreenMsg,
        VerticalMenu, VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

const TIMEOUT_MS: u32 = 2000;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmWithMenu {
    Value,
    Menu,
}

impl FlowController for ConfirmWithMenu {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Value, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Value, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Info),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Cancelled) => Self::Value.goto(),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::too_many_arguments)]
pub fn new_confirm_with_menu<T: AllowedTextContent + MaybeTrace + 'static>(
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    content: T,
    confirm_label: Option<TString<'static>>,
    hold: bool,
    extra_menu_label: Option<TString<'static>>,
    cancel_menu_label: Option<TString<'static>>,
) -> Result<SwipeFlow, error::Error> {
    let cancel_menu_label = cancel_menu_label.unwrap_or(TR::buttons__cancel.into());

    // Value
    let confirm_button = if hold {
        let confirm_label = confirm_label.unwrap_or(TR::buttons__hold_to_confirm.into());
        Button::with_text(confirm_label)
            .styled(theme::button_confirm())
            .with_long_press(theme::LOCK_HOLD_DURATION)
    } else {
        let confirm_label = confirm_label.unwrap_or(TR::buttons__confirm.into());
        Button::with_text(confirm_label).styled(theme::button_default())
    };
    let content_value = TextScreen::new(content)
        .with_header(Header::new(title).with_menu_button())
        .with_action_bar(ActionBar::new_single(confirm_button))
        .with_subtitle(subtitle.unwrap_or(TString::empty()))
        .map(|msg| match msg {
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Menu => Some(FlowMsg::Info),
        });

    let mut menu_items = VerticalMenu::<ShortMenuVec>::empty();

    if let Some(extra_menu_label) = extra_menu_label {
        menu_items.item(Button::new_menu_item(
            extra_menu_label,
            theme::menu_item_title(),
        ));
    }

    menu_items.item(Button::new_menu_item(
        cancel_menu_label,
        theme::menu_item_title_orange(),
    ));

    let content_menu = VerticalMenuScreen::new(menu_items)
        .with_header(Header::new(TString::empty()).with_close_button())
        .map(move |msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let mut res = SwipeFlow::new(&ConfirmWithMenu::Value)?;
    res.add_page(&ConfirmWithMenu::Value, content_value)?
        .add_page(&ConfirmWithMenu::Menu, content_menu)?;
    Ok(res)
}
