use heapless::Vec;

use crate::{
    error,
    micropython::{iter::IterBuf, map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{
            swipe_detect::SwipeSettings, ButtonRequestExt, ComponentExt, MsgMap, SwipeDirection,
        },
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow,
        },
        layout::obj::LayoutObj,
    },
};

use super::{
    super::{
        component::{
            AddressDetails, Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent, VerticalMenu,
            VerticalMenuChoiceMsg,
        },
        theme,
    },
    util::{ConfirmBlobParams, ShowInfoParams},
};

const MENU_ITEM_CANCEL: usize = 0;
const MENU_ITEM_FEE_INFO: usize = 1;
const MENU_ITEM_ACCOUNT_INFO: usize = 2;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmOutput {
    Address,
    Menu,
    AccountInfo,
    CancelTap,
}

impl FlowState for ConfirmOutput {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Address, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Address, SwipeDirection::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, SwipeDirection::Right) => Self::Address.swipe(direction),
            (Self::Menu, SwipeDirection::Left) => Self::AccountInfo.swipe(direction),
            (Self::AccountInfo | Self::CancelTap, SwipeDirection::Right) => {
                Self::Menu.swipe(direction)
            }
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (_, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => Self::CancelTap.swipe_left(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => Self::AccountInfo.transit(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Address.swipe_right(),
            (Self::CancelTap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (_, FlowMsg::Cancelled) => Self::Menu.transit(),
            _ => self.do_nothing(),
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmOutputWithAmount {
    Address,
    Amount,
    Menu,
    AccountInfo,
    CancelTap,
}

impl FlowState for ConfirmOutputWithAmount {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Address | Self::Amount, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Address, SwipeDirection::Up) => Self::Amount.swipe(direction),
            (Self::Amount, SwipeDirection::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Amount, SwipeDirection::Down) => Self::Address.swipe(direction),
            (Self::Menu, SwipeDirection::Right) => Self::Address.swipe(direction),
            (Self::AccountInfo | Self::CancelTap, SwipeDirection::Right) => {
                Self::Menu.swipe(direction)
            }
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (_, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => Self::CancelTap.swipe_left(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => Self::AccountInfo.transit(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Address.swipe_right(),
            (Self::CancelTap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (_, FlowMsg::Cancelled) => Self::Menu.transit(),
            _ => self.do_nothing(),
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmOutputWithSummary {
    Address,
    AddressMenu,
    AddressMenuCancel,
    Summary,
    SummaryMenu,
    SummaryMenuCancel,
    FeeInfo,
    Hold,
    HoldMenu,
    HoldMenuCancel,
    AccountInfo,
}

impl FlowState for ConfirmOutputWithSummary {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Address, SwipeDirection::Left) => Self::AddressMenu.swipe(direction),
            (Self::Address, SwipeDirection::Up) => Self::Summary.swipe(direction),
            (Self::AccountInfo, SwipeDirection::Right) => Self::AddressMenu.swipe(direction),
            (Self::Summary, SwipeDirection::Left) => Self::SummaryMenu.swipe(direction),
            (Self::Summary, SwipeDirection::Up) => Self::Hold.swipe(direction),
            (Self::Summary, SwipeDirection::Down) => Self::Address.swipe(direction),
            (Self::FeeInfo, SwipeDirection::Right) => Self::SummaryMenu.swipe(direction),
            (Self::Hold, SwipeDirection::Left) => Self::HoldMenu.swipe(direction),
            (Self::Hold, SwipeDirection::Down) => Self::Summary.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Address, FlowMsg::Info) => Self::AddressMenu.transit(),
            (Self::AddressMenu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => {
                Self::AddressMenuCancel.swipe_left()
            }
            (Self::AddressMenuCancel, FlowMsg::Cancelled) => Self::AddressMenu.swipe_right(),
            (Self::Summary, FlowMsg::Info) => Self::SummaryMenu.transit(),
            (Self::SummaryMenu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => {
                Self::SummaryMenuCancel.swipe_left()
            }
            (Self::SummaryMenuCancel, FlowMsg::Cancelled) => Self::SummaryMenu.swipe_right(),
            (Self::Hold, FlowMsg::Info) => Self::HoldMenu.transit(),
            (Self::HoldMenu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => {
                Self::HoldMenuCancel.swipe_left()
            }
            (Self::HoldMenuCancel, FlowMsg::Cancelled) => Self::HoldMenu.swipe_right(),
            (Self::SummaryMenu, FlowMsg::Choice(MENU_ITEM_FEE_INFO)) => Self::FeeInfo.swipe_left(),
            (Self::AddressMenu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => {
                Self::AccountInfo.swipe_left()
            }
            (Self::AddressMenu, FlowMsg::Cancelled) => Self::Address.swipe_right(),
            (Self::SummaryMenu, FlowMsg::Cancelled) => Self::Summary.swipe_right(),
            (Self::FeeInfo, FlowMsg::Cancelled) => Self::SummaryMenu.swipe_right(),
            (Self::HoldMenu, FlowMsg::Cancelled) => Self::Hold.swipe_right(),
            (
                Self::AddressMenuCancel | Self::SummaryMenuCancel | Self::HoldMenuCancel,
                FlowMsg::Confirmed,
            ) => self.return_msg(FlowMsg::Cancelled),
            (Self::Address, FlowMsg::Cancelled) => Self::AddressMenu.transit(),
            (Self::Summary, FlowMsg::Cancelled) => Self::SummaryMenu.transit(),
            (Self::Hold, FlowMsg::Cancelled) => Self::HoldMenu.transit(),
            (Self::Hold, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

fn get_cancel_page(
) -> MsgMap<Frame<SwipeContent<PromptScreen>>, impl Fn(FrameMsg<PromptMsg>) -> Option<FlowMsg>> {
    Frame::left_aligned(
        TR::send__cancel_sign.into(),
        SwipeContent::new(PromptScreen::new_tap_to_cancel()),
    )
    .with_cancel_button()
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .with_swipe(SwipeDirection::Down, SwipeSettings::default())
    .with_swipe(SwipeDirection::Left, SwipeSettings::default())
    .map(|msg| match msg {
        FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
        FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        _ => None,
    })
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_confirm_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, new_confirm_output_obj) }
}

fn new_confirm_output_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
    let title: Option<TString> = kwargs.get(Qstr::MP_QSTR_title)?.try_into_option()?;

    let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
    let account_path: Option<TString> =
        kwargs.get(Qstr::MP_QSTR_account_path)?.try_into_option()?;

    let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;
    let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;

    let address: Obj = kwargs.get(Qstr::MP_QSTR_address)?;
    let amount: Option<Obj> = kwargs.get(Qstr::MP_QSTR_amount)?.try_into_option()?;

    let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
    let text_mono: bool = kwargs.get_or(Qstr::MP_QSTR_text_mono, true)?;

    let summary_items: Obj = kwargs.get(Qstr::MP_QSTR_summary_items)?;
    let fee_items: Obj = kwargs.get(Qstr::MP_QSTR_fee_items)?;

    let summary_title: Option<TString> =
        kwargs.get(Qstr::MP_QSTR_summary_title)?.try_into_option()?;
    let summary_br_name: Option<TString> = kwargs
        .get(Qstr::MP_QSTR_summary_br_name)?
        .try_into_option()?;
    let summary_br_code: Option<u16> = kwargs
        .get(Qstr::MP_QSTR_summary_br_code)?
        .try_into_option()?;

    let cancel_text: Option<TString> = kwargs.get(Qstr::MP_QSTR_cancel_text)?.try_into_option()?;

    // Address
    let content_address = ConfirmBlobParams::new(TR::words__address.into(), address, None)
        .with_subtitle(title)
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_chunkify(chunkify)
        .with_text_mono(text_mono)
        .into_layout()?
        .one_button_request(ButtonRequest::from_num(br_code, br_name));

    // AddressMenu
    let mut address_menu = VerticalMenu::empty();
    let mut address_menu_items = Vec::<usize, 2>::new();
    if account.is_some() && account_path.is_some() {
        address_menu = address_menu.item(
            theme::ICON_CHEVRON_RIGHT,
            TR::address_details__account_info.into(),
        );
        unwrap!(address_menu_items.push(MENU_ITEM_ACCOUNT_INFO));
    }
    address_menu = address_menu.danger(
        theme::ICON_CANCEL,
        cancel_text.unwrap_or(TR::send__cancel_sign.into()),
    );
    unwrap!(address_menu_items.push(MENU_ITEM_CANCEL));
    let content_address_menu = Frame::left_aligned(TString::empty(), address_menu)
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(move |msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => {
                let selected_item = address_menu_items[i];
                Some(FlowMsg::Choice(selected_item))
            }
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

    // AccountInfo
    let ad = AddressDetails::new(TR::send__send_from.into(), account, account_path)?;
    let content_account = ad.map(|_| Some(FlowMsg::Cancelled));

    let res = if amount.is_some() {
        let content_amount = ConfirmBlobParams::new(
            TR::words__amount.into(),
            amount.unwrap_or(Obj::const_none()),
            None,
        )
        .with_subtitle(title)
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_text_mono(text_mono)
        .with_swipe_down()
        .into_layout()?
        .one_button_request(ButtonRequest::from_num(br_code, br_name));

        SwipeFlow::new(&ConfirmOutputWithAmount::Address)?
            .with_page(&ConfirmOutputWithAmount::Address, content_address)?
            .with_page(&ConfirmOutputWithAmount::Amount, content_amount)?
            .with_page(&ConfirmOutputWithAmount::Menu, content_address_menu)?
            .with_page(&ConfirmOutputWithAmount::AccountInfo, content_account)?
            .with_page(&ConfirmOutputWithAmount::CancelTap, get_cancel_page())?
    } else if summary_items != Obj::const_none() {
        // Summary
        let mut summary =
            ShowInfoParams::new(summary_title.unwrap_or(TR::words__title_summary.into()))
                .with_menu_button()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe_up()
                .with_swipe_down();
        for pair in IterBuf::new().try_iterate(summary_items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            summary = unwrap!(summary.add(label, value));
        }
        let content_summary = summary
            .into_layout()?
            .one_button_request(ButtonRequest::from_num(
                summary_br_code.unwrap(),
                summary_br_name.unwrap(),
            ))
            .with_pages(|summary_pages| summary_pages + 1);

        // Hold
        let content_hold = Frame::left_aligned(
            TR::send__sign_transaction.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_menu_button()
        .with_footer(TR::instructions__hold_to_sign.into(), None)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            _ => None,
        });

        // FeeInfo
        let mut has_fee_info = false;
        let mut fee = ShowInfoParams::new(TR::confirm_total__title_fee.into()).with_cancel_button();
        if fee_items != Obj::const_none() {
            for pair in IterBuf::new().try_iterate(fee_items)? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                fee = unwrap!(fee.add(label, value));
                has_fee_info = true;
            }
        }
        let content_fee = fee.into_layout()?;

        // SummaryMenu
        let mut summary_menu = VerticalMenu::empty();
        let mut summary_menu_items = Vec::<usize, 2>::new();
        if has_fee_info {
            summary_menu = summary_menu.item(
                theme::ICON_CHEVRON_RIGHT,
                TR::confirm_total__title_fee.into(),
            );
            unwrap!(summary_menu_items.push(MENU_ITEM_FEE_INFO));
        }
        summary_menu = summary_menu.danger(
            theme::ICON_CANCEL,
            cancel_text.unwrap_or(TR::send__cancel_sign.into()),
        );
        unwrap!(summary_menu_items.push(MENU_ITEM_CANCEL));
        let content_summary_menu = Frame::left_aligned(TString::empty(), summary_menu)
            .with_cancel_button()
            .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
            .map(move |msg| match msg {
                FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => {
                    let selected_item = summary_menu_items[i];
                    Some(FlowMsg::Choice(selected_item))
                }
                FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
            });

        // HoldMenu
        let hold_menu = VerticalMenu::empty().danger(
            theme::ICON_CANCEL,
            cancel_text.unwrap_or(TR::send__cancel_sign.into()),
        );
        let content_hold_menu = Frame::left_aligned(TString::empty(), hold_menu)
            .with_cancel_button()
            .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
            .map(move |msg| match msg {
                FrameMsg::Content(VerticalMenuChoiceMsg::Selected(_)) => {
                    Some(FlowMsg::Choice(MENU_ITEM_CANCEL))
                }
                FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
            });

        SwipeFlow::new(&ConfirmOutputWithSummary::Address)?
            .with_page(&ConfirmOutputWithSummary::Address, content_address)?
            .with_page(&ConfirmOutputWithSummary::AddressMenu, content_address_menu)?
            .with_page(
                &ConfirmOutputWithSummary::AddressMenuCancel,
                get_cancel_page(),
            )?
            .with_page(&ConfirmOutputWithSummary::Summary, content_summary)?
            .with_page(&ConfirmOutputWithSummary::SummaryMenu, content_summary_menu)?
            .with_page(
                &ConfirmOutputWithSummary::SummaryMenuCancel,
                get_cancel_page(),
            )?
            .with_page(&ConfirmOutputWithSummary::FeeInfo, content_fee)?
            .with_page(&ConfirmOutputWithSummary::Hold, content_hold)?
            .with_page(&ConfirmOutputWithSummary::HoldMenu, content_hold_menu)?
            .with_page(&ConfirmOutputWithSummary::HoldMenuCancel, get_cancel_page())?
            .with_page(&ConfirmOutputWithSummary::AccountInfo, content_account)?
    } else {
        SwipeFlow::new(&ConfirmOutput::Address)?
            .with_page(&ConfirmOutput::Address, content_address)?
            .with_page(&ConfirmOutput::Menu, content_address_menu)?
            .with_page(&ConfirmOutput::AccountInfo, content_account)?
            .with_page(&ConfirmOutput::CancelTap, get_cancel_page())?
    };

    Ok(LayoutObj::new(res)?.into())
}
