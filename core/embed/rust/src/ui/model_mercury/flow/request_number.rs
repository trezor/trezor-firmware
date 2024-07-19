use crate::{
    error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, Paragraphs},
            ButtonRequestExt, ComponentExt, SwipeDirection,
        },
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow,
        },
        layout::obj::LayoutObj,
        model_mercury::component::SwipeContent,
    },
};

use super::super::{
    component::{
        CancelInfoConfirmMsg, Frame, FrameMsg, NumberInputDialog, NumberInputDialogMsg,
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

impl FlowState for RequestNumber {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Number, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Menu, SwipeDirection::Right) => Self::Number.swipe(direction),
            (Self::Info, SwipeDirection::Right) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Number, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::Info.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Number.swipe_right(),
            (Self::Info, FlowMsg::Cancelled) => Self::Menu.transit(),
            (Self::Number, FlowMsg::Choice(n)) => self.return_msg(FlowMsg::Choice(n)),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_request_number(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, RequestNumber::new_obj) }
}

impl RequestNumber {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let count: u32 = kwargs.get(Qstr::MP_QSTR_count)?.try_into()?;
        let min_count: u32 = kwargs.get(Qstr::MP_QSTR_min_count)?.try_into()?;
        let max_count: u32 = kwargs.get(Qstr::MP_QSTR_max_count)?.try_into()?;
        let description: Obj = kwargs.get(Qstr::MP_QSTR_description)?;
        let info: Obj = kwargs.get(Qstr::MP_QSTR_info)?;
        assert!(description != Obj::const_none());
        assert!(info != Obj::const_none());
        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;

        let description_cb = move |i: u32| {
            TString::try_from(
                description
                    .call_with_n_args(&[i.try_into().unwrap()])
                    .unwrap(),
            )
            .unwrap()
        };
        let info_cb = move |i: u32| {
            TString::try_from(info.call_with_n_args(&[i.try_into().unwrap()]).unwrap()).unwrap()
        };

        let number_input_dialog =
            NumberInputDialog::new(min_count, max_count, count, description_cb)?;
        let content_number_input =
            Frame::left_aligned(title, SwipeContent::new(number_input_dialog))
                .with_menu_button()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(SwipeDirection::Up, SwipeSettings::default())
                .with_swipe(SwipeDirection::Left, SwipeSettings::default())
                .map(|msg| match msg {
                    FrameMsg::Button(_) => Some(FlowMsg::Info),
                    FrameMsg::Content(NumberInputDialogMsg(n)) => Some(FlowMsg::Choice(n as usize)),
                })
                .one_button_request(ButtonRequest::from_num(br_code, br_name));

        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty().item(theme::ICON_CHEVRON_RIGHT, TR::buttons__more_info.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            FrameMsg::Button(_) => None,
        });

        let paragraphs_info = Paragraphs::new(Paragraph::new(
            &theme::TEXT_MAIN_GREY_LIGHT,
            info_cb(0), // TODO: get the value
        ));
        let content_info = Frame::left_aligned(
            TR::backup__title_skip.into(),
            SwipeContent::new(paragraphs_info),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            _ => None,
        });

        let res = SwipeFlow::new(&RequestNumber::Number)?
            .with_page(&RequestNumber::Number, content_number_input)?
            .with_page(&RequestNumber::Menu, content_menu)?
            .with_page(&RequestNumber::Info, content_info)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
