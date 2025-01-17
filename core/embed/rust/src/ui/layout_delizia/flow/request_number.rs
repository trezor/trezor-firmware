use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{swipe_detect::SwipeSettings, ComponentExt},
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
    },
};

use core::sync::atomic::{AtomicU16, Ordering};

use super::super::{
    component::{
        Frame, FrameMsg, NumberInputDialog, NumberInputDialogMsg, SwipeContent, UpdatableMoreInfo,
        VerticalMenu, VerticalMenuChoiceMsg,
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

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Number, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Number.swipe(direction),
            (Self::Info, Direction::Right) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Number, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::Info.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Number.swipe_right(),
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

    let number_input_dialog = NumberInputDialog::new(min_count, max_count, count, description)?;
    let content_number_input = Frame::left_aligned(title, SwipeContent::new(number_input_dialog))
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(Direction::Up, SwipeSettings::default())
        .with_swipe(Direction::Left, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            FrameMsg::Content(NumberInputDialogMsg::Changed(n)) => {
                NUM_DISPLAYED.store(n as u16, Ordering::Relaxed);
                None
            }
            FrameMsg::Content(NumberInputDialogMsg::Confirmed(n)) => {
                NUM_DISPLAYED.store(n as u16, Ordering::Relaxed);
                Some(FlowMsg::Choice(n as usize))
            }
        });

    let content_menu = Frame::left_aligned(
        TString::empty(),
        VerticalMenu::empty().item(theme::ICON_CHEVRON_RIGHT, TR::buttons__more_info.into()),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(|msg| match msg {
        FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
        FrameMsg::Button(FlowMsg::Cancelled) => Some(FlowMsg::Cancelled),
        FrameMsg::Button(_) => None,
    });

    let updatable_info = UpdatableMoreInfo::new(info_closure);
    let content_info = Frame::left_aligned(TString::empty(), SwipeContent::new(updatable_info))
        .with_cancel_button()
        .with_swipe(Direction::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Button(FlowMsg::Cancelled) => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let res = SwipeFlow::new(&RequestNumber::Number)?
        .with_page(&RequestNumber::Number, content_number_input)?
        .with_page(&RequestNumber::Menu, content_menu)?
        .with_page(&RequestNumber::Info, content_info)?;
    Ok(res)
}
