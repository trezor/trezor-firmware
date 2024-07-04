use crate::{
    error,
    micropython::{iter::IterBuf, map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{swipe_detect::SwipeSettings, ButtonRequestExt, ComponentExt, SwipeDirection},
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow,
        },
        layout::obj::LayoutObj,
        model_mercury::component::SwipeContent,
    },
};

use super::{
    super::{
        component::{Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg},
        theme,
    },
    util::ShowInfoParams,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmSummary {
    Summary,
    Hold,
    Menu,
    FeeInfo,
    AccountInfo,
    CancelTap,
}

impl FlowState for ConfirmSummary {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Summary | Self::Hold, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Summary, SwipeDirection::Up) => Self::Hold.swipe(direction),
            (Self::Hold, SwipeDirection::Down) => Self::Summary.swipe(direction),
            (Self::Menu, SwipeDirection::Right) => Self::Summary.swipe(direction),
            (Self::Menu, SwipeDirection::Left) => Self::FeeInfo.swipe(direction),
            (Self::AccountInfo | Self::FeeInfo | Self::CancelTap, SwipeDirection::Right) => {
                Self::Menu.swipe(direction)
            }
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (_, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Hold, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(0)) => Self::FeeInfo.swipe_left(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::AccountInfo.swipe_left(),
            (Self::Menu, FlowMsg::Choice(2)) => Self::CancelTap.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Summary.swipe_right(),
            (Self::CancelTap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (_, FlowMsg::Cancelled) => Self::Menu.transit(),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_confirm_summary(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ConfirmSummary::new_obj) }
}

impl ConfirmSummary {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let account_items: Obj = kwargs.get(Qstr::MP_QSTR_account_items)?;
        let fee_items: Obj = kwargs.get(Qstr::MP_QSTR_fee_items)?;
        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;

        // Summary
        let mut summary = ShowInfoParams::new(title)
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .with_swipe_up();
        for pair in IterBuf::new().try_iterate(items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            summary = unwrap!(summary.add(label, value));
        }
        let content_summary = summary
            .into_layout()?
            .one_button_request(ButtonRequest::from_num(br_code, br_name))
            // Summary(1) + Hold(1)
            .with_pages(|summary_pages| summary_pages + 1);

        // Hold to confirm
        let content_hold = Frame::left_aligned(
            TR::send__sign_transaction.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_menu_button()
        .with_footer(TR::instructions__hold_to_sign.into(), None)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Info),
        });

        // Menu
        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty()
                .item(theme::ICON_CHEVRON_RIGHT, "Fee info".into())
                .item(theme::ICON_CHEVRON_RIGHT, "Account info".into())
                .danger(theme::ICON_CANCEL, "Cancel sign".into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        // FeeInfo
        let mut fee = ShowInfoParams::new(TR::confirm_total__title_fee.into()).with_cancel_button();
        for pair in IterBuf::new().try_iterate(fee_items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            fee = unwrap!(fee.add(label, value));
        }
        let content_fee = fee.into_layout()?;

        // AccountInfo
        let mut account = ShowInfoParams::new(TR::send__send_from.into()).with_cancel_button();
        for pair in IterBuf::new().try_iterate(account_items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            account = unwrap!(account.add(label, value));
        }
        let content_account = account.into_layout()?;

        // CancelTap
        let content_cancel_tap = Frame::left_aligned(
            TR::send__cancel_sign.into(),
            PromptScreen::new_tap_to_cancel(),
        )
        .with_cancel_button()
        .with_footer(TR::instructions__tap_to_confirm.into(), None)
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let res = SwipeFlow::new(&ConfirmSummary::Summary)?
            .with_page(&ConfirmSummary::Summary, content_summary)?
            .with_page(&ConfirmSummary::Hold, content_hold)?
            .with_page(&ConfirmSummary::Menu, content_menu)?
            .with_page(&ConfirmSummary::FeeInfo, content_fee)?
            .with_page(&ConfirmSummary::AccountInfo, content_account)?
            .with_page(&ConfirmSummary::CancelTap, content_cancel_tap)?;

        Ok(LayoutObj::new(res)?.into())
    }
}
