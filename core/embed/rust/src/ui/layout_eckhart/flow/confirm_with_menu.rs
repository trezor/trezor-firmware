use heapless::Vec;

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
        ActionBar, AllowedTextContent, Header, Hint, ShortMenuVec, TextScreen, TextScreenMsg,
        VerticalMenu, VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme::{self, gradient::Gradient},
};

const TIMEOUT_MS: u32 = 2000;
const MENU_ITEM_CANCEL: usize = 0;
const MENU_ITEM_INFO: usize = 1;

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
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_INFO)) => self.return_msg(FlowMsg::Info),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => self.return_msg(FlowMsg::Cancelled),
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
    hint: Option<TString<'static>>,
    verb: Option<TString<'static>>,
    hold: bool,
    extra_menu_label: Option<TString<'static>>,
    cancel_menu_label: Option<TString<'static>>,
) -> Result<SwipeFlow, error::Error> {
    let cancel_menu_label = cancel_menu_label.unwrap_or(TR::buttons__cancel.into());

    // Value
    let confirm_button = if hold {
        let verb = verb.unwrap_or(TR::buttons__hold_to_confirm.into());
        Button::with_text(verb)
            .with_long_press(theme::CONFIRM_HOLD_DURATION)
            .styled(theme::firmware::button_confirm())
            .with_gradient(Gradient::SignGreen)
    } else if let Some(verb) = verb {
        Button::with_text(verb)
    } else {
        Button::with_text(TR::buttons__confirm.into())
            .styled(theme::firmware::button_confirm())
            .with_gradient(Gradient::SignGreen)
    };

    let mut value_screen = TextScreen::new(content)
        .with_header(Header::new(title).with_menu_button())
        .with_action_bar(ActionBar::new_single(confirm_button))
        .with_subtitle(subtitle.unwrap_or(TString::empty()));
    if let Some(hint) = hint {
        value_screen = value_screen.with_hint(Hint::new_instruction(hint, Some(theme::ICON_INFO)));
    }
    let content_value = value_screen.map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        TextScreenMsg::Menu => Some(FlowMsg::Info),
    });

    // Menu
    let mut menu = VerticalMenu::<ShortMenuVec>::empty();
    let mut menu_items = Vec::<usize, 2>::new();

    if let Some(extra_menu_label) = extra_menu_label {
        menu.item(Button::new_menu_item(
            extra_menu_label,
            theme::menu_item_title(),
        ));
        unwrap!(menu_items.push(MENU_ITEM_INFO));
    }

    menu.item(Button::new_menu_item(
        cancel_menu_label,
        theme::menu_item_title_orange(),
    ));
    unwrap!(menu_items.push(MENU_ITEM_CANCEL));

    let content_menu = VerticalMenuScreen::new(menu)
        .with_header(Header::new(TString::empty()).with_close_button())
        .map(move |msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => {
                let selected_item = menu_items[i];
                Some(FlowMsg::Choice(selected_item))
            }
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let mut res = SwipeFlow::new(&ConfirmWithMenu::Value)?;
    res.add_page(&ConfirmWithMenu::Value, content_value)?
        .add_page(&ConfirmWithMenu::Menu, content_menu)?;
    Ok(res)
}
