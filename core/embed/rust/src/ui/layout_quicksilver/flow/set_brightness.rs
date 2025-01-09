use core::sync::atomic::{AtomicU8, Ordering};

use crate::{
    error::Error,
    storage,
    translations::TR,
    trezorhal::display,
    ui::{
        component::{base::ComponentExt, swipe_detect::SwipeSettings, FlowMsg},
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::{
        number_input_slider::{NumberInputSliderDialog, NumberInputSliderDialogMsg},
        Frame, FrameMsg, PromptMsg, PromptScreen, StatusScreen, SwipeContent, VerticalMenu,
        VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum SetBrightness {
    Slider,
    Menu,
    Confirm,
    Confirmed,
}

impl FlowController for SetBrightness {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Menu, Direction::Right) => Self::Slider.swipe(direction),
            (Self::Slider, Direction::Up) => Self::Confirm.swipe(direction),
            (Self::Confirm, Direction::Down) => Self::Slider.swipe(direction),
            (Self::Confirm, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Confirmed, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Slider, FlowMsg::Info) => Self::Menu.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Slider.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Confirm, FlowMsg::Confirmed) => Self::Confirmed.swipe_up(),
            (Self::Confirm, FlowMsg::Info) => Self::Menu.swipe_left(),
            (Self::Confirmed, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

static BRIGHTNESS: AtomicU8 = AtomicU8::new(0);

pub fn new_set_brightness(brightness: Option<u8>) -> Result<SwipeFlow, Error> {
    let brightness = brightness.unwrap_or(theme::backlight::get_backlight_normal());
    let content_slider = Frame::left_aligned(
        TR::brightness__title.into(),
        NumberInputSliderDialog::new(
            theme::backlight::get_backlight_min() as u16,
            theme::backlight::get_backlight_max() as u16,
            brightness as u16,
        ),
    )
    .with_subtitle(TR::homescreen__settings_subtitle.into())
    .with_menu_button()
    .with_swipe(Direction::Up, SwipeSettings::default())
    .map(|msg| match msg {
        FrameMsg::Content(NumberInputSliderDialogMsg::Changed(n)) => {
            display::backlight(n as _);
            BRIGHTNESS.store(n as u8, Ordering::Relaxed);
            None
        }
        FrameMsg::Button(_) => Some(FlowMsg::Info),
    });

    let content_menu = Frame::left_aligned(
        "".into(),
        VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::buttons__cancel.into()),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(move |msg| match msg {
        FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
        FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
    });

    let content_confirm = Frame::left_aligned(
        TR::brightness__change_title.into(),
        SwipeContent::new(PromptScreen::new_tap_to_confirm()),
    )
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .with_menu_button()
    .with_swipe(Direction::Down, SwipeSettings::default())
    .with_swipe(Direction::Left, SwipeSettings::default())
    .map(move |msg| match msg {
        FrameMsg::Content(PromptMsg::Confirmed) => {
            let _ = storage::set_brightness(BRIGHTNESS.load(Ordering::Relaxed));
            Some(FlowMsg::Confirmed)
        }
        FrameMsg::Button(_) => Some(FlowMsg::Info),
        _ => None,
    });

    let content_confirmed = Frame::left_aligned(
        TR::words__title_success.into(),
        SwipeContent::new(StatusScreen::new_success(
            TR::brightness__changed_title.into(),
        ))
        .with_no_attach_anim(),
    )
    .with_footer(TR::instructions__swipe_up.into(), None)
    .with_swipe(Direction::Up, SwipeSettings::default())
    .with_result_icon(theme::ICON_BULLET_CHECKMARK, theme::GREEN_LIGHT)
    .map(move |_msg| Some(FlowMsg::Confirmed));

    let res = SwipeFlow::new(&SetBrightness::Slider)?
        .with_page(&SetBrightness::Slider, content_slider)?
        .with_page(&SetBrightness::Menu, content_menu)?
        .with_page(&SetBrightness::Confirm, content_confirm)?
        .with_page(&SetBrightness::Confirmed, content_confirmed)?;

    Ok(res)
}
