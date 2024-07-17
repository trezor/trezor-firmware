use core::sync::atomic::{AtomicU8, Ordering};

use crate::{
    error::Error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    storage,
    translations::TR,
    trezorhal::display,
    ui::{
        component::{base::ComponentExt, swipe_detect::SwipeSettings, SwipeDirection},
        flow::{
            base::{DecisionBuilder as _, FlowMsg, StateChange},
            FlowState, SwipeFlow,
        },
        layout::obj::LayoutObj,
        model_mercury::component::{
            number_input_slider::{NumberInputSliderDialog, NumberInputSliderDialogMsg},
            SwipeContent,
        },
    },
};

use super::super::{
    component::{Frame, FrameMsg, PromptScreen, StatusScreen, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum SetBrightness {
    Slider,
    Menu,
    Confirm,
    Confirmed,
}

impl FlowState for SetBrightness {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Menu, SwipeDirection::Right) => Self::Slider.swipe(direction),
            (Self::Slider, SwipeDirection::Up) => Self::Confirm.swipe(direction),
            (Self::Confirm, SwipeDirection::Down) => Self::Slider.swipe(direction),
            (Self::Confirm, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Confirmed, SwipeDirection::Up) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
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

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_set_brightness(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, SetBrightness::new_obj) }
}

impl SetBrightness {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, Error> {
        let current: Option<u8> = kwargs.get(Qstr::MP_QSTR_current)?.try_into_option()?;
        let content_slider = Frame::left_aligned(
            TR::brightness__title.into(),
            NumberInputSliderDialog::new(
                theme::backlight::get_backlight_min() as u16,
                theme::backlight::get_backlight_max() as u16,
                current.unwrap_or(theme::backlight::get_backlight_normal()) as u16,
            ),
        )
        .with_subtitle(TR::homescreen__settings_subtitle.into())
        .with_menu_button()
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
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
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
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
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .map(move |msg| match msg {
            FrameMsg::Content(()) => {
                let _ = storage::set_brightness(BRIGHTNESS.load(Ordering::Relaxed));
                Some(FlowMsg::Confirmed)
            }
            FrameMsg::Button(_) => Some(FlowMsg::Info),
        });

        let content_confirmed = Frame::left_aligned(
            TR::words__title_success.into(),
            SwipeContent::new(StatusScreen::new_success(
                TR::brightness__changed_title.into(),
            ))
            .with_no_attach_anim(),
        )
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .map(move |_msg| Some(FlowMsg::Confirmed));

        let res = SwipeFlow::new(&SetBrightness::Slider)?
            .with_page(&SetBrightness::Slider, content_slider)?
            .with_page(&SetBrightness::Menu, content_menu)?
            .with_page(&SetBrightness::Confirm, content_confirm)?
            .with_page(&SetBrightness::Confirmed, content_confirmed)?;

        Ok(LayoutObj::new(res)?.into())
    }
}
