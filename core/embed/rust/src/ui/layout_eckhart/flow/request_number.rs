use crate::{
    error,
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

use core::sync::atomic::{AtomicU16, Ordering};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, NumberInput, ShortMenuVec, UpdatableInfoScreen, ValueInputScreen,
        ValueInputScreenMsg, VerticalMenu, VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum RequestNumber {
    Number,
    Menu,
    Info,
}

impl FlowController for RequestNumber {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Number, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::Info.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Cancelled) => Self::Number.goto(),
            (Self::Info, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Number, FlowMsg::Choice(n)) => self.return_msg(FlowMsg::Choice(n)),
            _ => self.do_nothing(),
        }
    }
}

static NUM_DISPLAYED: AtomicU16 = AtomicU16::new(0);

#[allow(clippy::too_many_arguments)]
pub fn new_request_number(
    title: TString<'static>,
    count: u32,
    min_count: u32,
    max_count: u32,
    description: TString<'static>,
    info_closure: impl Fn(u32) -> TString<'static> + 'static,
) -> Result<SwipeFlow, error::Error> {
    NUM_DISPLAYED.store(count as u16, Ordering::Relaxed);

    // wrap the closure for obtaining MoreInfo text and call it with NUM_DISPLAYED
    let info_closure = move || {
        let curr_number = NUM_DISPLAYED.load(Ordering::Relaxed);
        info_closure(curr_number as u32)
    };

    let content_input =
        ValueInputScreen::new(NumberInput::new(min_count, max_count, count), description)
            .with_header(Header::new(title).with_menu_button())
            .with_action_bar(ActionBar::new_single(Button::with_text(
                TR::buttons__confirm.into(),
            )))
            .with_changed_value_handling()
            .map(|msg| match msg {
                ValueInputScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
                ValueInputScreenMsg::Confirmed(n) => {
                    NUM_DISPLAYED.store(n as u16, Ordering::Relaxed);
                    Some(FlowMsg::Choice(n as usize))
                }
                ValueInputScreenMsg::Changed(n) => {
                    NUM_DISPLAYED.store(n as u16, Ordering::Relaxed);
                    None
                }
                ValueInputScreenMsg::Menu => Some(FlowMsg::Info),
            });

    let menu_items = VerticalMenu::<ShortMenuVec>::empty()
        .with_item(Button::new_menu_item(
            TR::buttons__more_info.into(),
            theme::menu_item_title(),
        ))
        .with_item(Button::new_cancel_menu_item(TR::buttons__cancel.into()));

    let content_menu = VerticalMenuScreen::new(menu_items)
        .with_header(Header::new(title).with_close_button())
        .map(move |msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let content_info = UpdatableInfoScreen::new(info_closure)
        .with_header(Header::new(title).with_close_button())
        .map(|_| Some(FlowMsg::Cancelled));

    let mut res = SwipeFlow::new(&RequestNumber::Number)?;
    res.add_page(&RequestNumber::Number, content_input)?
        .add_page(&RequestNumber::Menu, content_menu)?
        .add_page(&RequestNumber::Info, content_info)?;
    Ok(res)
}
