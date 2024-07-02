use core::sync::atomic::{AtomicU16, Ordering};

use crate::{
    error::Error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    storage,
    translations::TR,
    trezorhal::display,
    ui::{
        component::{base::ComponentExt, swipe_detect::SwipeSettings, SwipeDirection},
        flow::{
            base::{Decision, FlowMsg},
            flow_store, FlowState, FlowStore, SwipeFlow,
        },
        layout::obj::LayoutObj,
        model_mercury::component::{
            number_input_slider::{NumberInputSliderDialog, NumberInputSliderDialogMsg},
            SwipeContent,
        },
    },
};

use super::super::{
    component::{Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum SetBrightness {
    Slider,
    Menu,
    Confirm,
}

impl FlowState for SetBrightness {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (SetBrightness::Menu, SwipeDirection::Right) => {
                Decision::Goto(SetBrightness::Slider, direction)
            }
            (SetBrightness::Slider, SwipeDirection::Up) => {
                Decision::Goto(SetBrightness::Confirm, direction)
            }
            (SetBrightness::Confirm, SwipeDirection::Down) => {
                Decision::Goto(SetBrightness::Slider, direction)
            }
            (SetBrightness::Confirm, SwipeDirection::Left) => {
                Decision::Goto(SetBrightness::Menu, direction)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (SetBrightness::Slider, FlowMsg::Info) => {
                Decision::Goto(SetBrightness::Menu, SwipeDirection::Left)
            }
            (SetBrightness::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(SetBrightness::Slider, SwipeDirection::Right)
            }
            (SetBrightness::Menu, FlowMsg::Choice(0)) => Decision::Return(FlowMsg::Cancelled),
            (SetBrightness::Confirm, FlowMsg::Confirmed) => Decision::Return(FlowMsg::Confirmed),
            (SetBrightness::Confirm, FlowMsg::Info) => {
                Decision::Goto(SetBrightness::Menu, SwipeDirection::Left)
            }
            _ => Decision::Nothing,
        }
    }
}

static BRIGHTNESS: AtomicU16 = AtomicU16::new(0);

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_set_brightness(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, SetBrightness::new_obj) }
}

impl SetBrightness {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, Error> {
        let current: Option<u16> = kwargs.get(Qstr::MP_QSTR_current)?.try_into_option()?;
        let content_slider = Frame::left_aligned(
            TR::brightness__title.into(),
            NumberInputSliderDialog::new(
                theme::backlight::get_backlight_min(),
                theme::backlight::get_backlight_max(),
                current.unwrap_or(theme::backlight::get_backlight_normal()),
            ),
        )
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Content(NumberInputSliderDialogMsg::Changed(n)) => {
                display::backlight(n as _);
                BRIGHTNESS.store(n, Ordering::Relaxed);
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
            TR::brightness__title.into(),
            SwipeContent::new(PromptScreen::new_tap_to_confirm()),
        )
        .with_footer(TR::instructions__tap_to_confirm.into(), None)
        .with_menu_button()
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .map(move |msg| match msg {
            FrameMsg::Content(()) => {
                let _ = storage::set_brightness(BRIGHTNESS.load(Ordering::Relaxed) as u8);
                Some(FlowMsg::Confirmed)
            }
            FrameMsg::Button(_) => Some(FlowMsg::Info),
        });

        let store = flow_store()
            .add(content_slider)?
            .add(content_menu)?
            .add(content_confirm)?;

        let res = SwipeFlow::new(SetBrightness::Slider, store)?;

        Ok(LayoutObj::new(res)?.into())
    }
}
