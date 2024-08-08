use heapless::Vec;

use crate::{
    error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
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
    util::ConfirmBlobParams,
};

const MENU_ITEM_CANCEL: usize = 0;
const MENU_ITEM_ACCOUNT_INFO: usize = 1;

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
            (Self::Menu, FlowMsg::Choice(0)) => Self::AccountInfo.transit(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::CancelTap.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Address.swipe_right(),
            (Self::CancelTap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (_, FlowMsg::Cancelled) => Self::Menu.transit(),
            _ => self.do_nothing(),
        }
    }
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

    // Menu
    let mut menu = VerticalMenu::empty();
    let mut menu_items = Vec::<usize, 3>::new();
    if account.is_some() && account_path.is_some() {
        menu = menu.item(
            theme::ICON_CHEVRON_RIGHT,
            TR::address_details__account_info.into(),
        );
        menu_items.push(MENU_ITEM_ACCOUNT_INFO);
    }
    menu = menu.danger(
        theme::ICON_CANCEL,
        cancel_text.unwrap_or(TR::send__cancel_sign.into()),
    );
    unwrap!(menu_items.push(MENU_ITEM_CANCEL));
    let content_menu = Frame::left_aligned(TString::empty(), menu)
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(move |msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => {
                let selected_item = menu_items[i];
                Some(FlowMsg::Choice(selected_item))
            }
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

    // AccountInfo
    let ad = AddressDetails::new(TR::send__send_from.into(), account, account_path)?;
    let content_account = ad.map(|_| Some(FlowMsg::Cancelled));

    // CancelTap
    let content_cancel_tap = Frame::left_aligned(
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
    });

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
            .with_page(&ConfirmOutputWithAmount::Menu, content_menu)?
            .with_page(&ConfirmOutputWithAmount::AccountInfo, content_account)?
            .with_page(&ConfirmOutputWithAmount::CancelTap, content_cancel_tap)?
    } else {
        SwipeFlow::new(&ConfirmOutput::Address)?
            .with_page(&ConfirmOutput::Address, content_address)?
            .with_page(&ConfirmOutput::Menu, content_menu)?
            .with_page(&ConfirmOutput::AccountInfo, content_account)?
            .with_page(&ConfirmOutput::CancelTap, content_cancel_tap)?
    };

    Ok(LayoutObj::new(res)?.into())
}
