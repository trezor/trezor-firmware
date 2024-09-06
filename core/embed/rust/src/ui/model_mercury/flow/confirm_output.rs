use heapless::Vec;

use crate::{
    error,
    micropython::{iter::IterBuf, map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{swipe_detect::SwipeSettings, ButtonRequestExt, ComponentExt, MsgMap},
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
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
const MENU_ITEM_ADDRESS_INFO: usize = 2;
const MENU_ITEM_ACCOUNT_INFO: usize = 3;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmOutput {
    Address,
    Menu,
    AccountInfo,
    CancelTap,
}

impl FlowController for ConfirmOutput {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Address, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Address, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, Direction::Right) => Self::Address.swipe(direction),
            (Self::Menu, Direction::Left) => Self::AccountInfo.swipe(direction),
            (Self::AccountInfo | Self::CancelTap, Direction::Right) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (_, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => Self::CancelTap.swipe_left(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => Self::AccountInfo.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Address.swipe_right(),
            (Self::CancelTap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (_, FlowMsg::Cancelled) => Self::Menu.goto(),
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

impl FlowController for ConfirmOutputWithAmount {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Address | Self::Amount, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Address, Direction::Up) => Self::Amount.swipe(direction),
            (Self::Amount, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Amount, Direction::Down) => Self::Address.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Address.swipe(direction),
            (Self::AccountInfo | Self::CancelTap, Direction::Right) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (_, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => Self::CancelTap.swipe_left(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => Self::AccountInfo.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Address.swipe_right(),
            (Self::CancelTap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (_, FlowMsg::Cancelled) => Self::Menu.goto(),
            _ => self.do_nothing(),
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmOutputWithSummary {
    Main,
    MainMenu,
    MainMenuCancel,
    AddressInfo,
    Summary,
    SummaryMenu,
    SummaryMenuCancel,
    FeeInfo,
    Hold,
    HoldMenu,
    HoldMenuCancel,
    AccountInfo,
}

impl FlowController for ConfirmOutputWithSummary {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Main, Direction::Left) => Self::MainMenu.swipe(direction),
            (Self::Main, Direction::Up) => Self::Summary.swipe(direction),
            (Self::MainMenu, Direction::Right) => Self::Main.swipe(direction),
            (Self::AddressInfo, Direction::Right) => Self::MainMenu.swipe(direction),
            (Self::AccountInfo, Direction::Right) => Self::MainMenu.swipe(direction),
            (Self::Summary, Direction::Left) => Self::SummaryMenu.swipe(direction),
            (Self::Summary, Direction::Up) => Self::Hold.swipe(direction),
            (Self::Summary, Direction::Down) => Self::Main.swipe(direction),
            (Self::SummaryMenu, Direction::Right) => Self::Summary.swipe(direction),
            (Self::FeeInfo, Direction::Right) => Self::SummaryMenu.swipe(direction),
            (Self::Hold, Direction::Left) => Self::HoldMenu.swipe(direction),
            (Self::Hold, Direction::Down) => Self::Summary.swipe(direction),
            (Self::HoldMenu, Direction::Right) => Self::Hold.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Main, FlowMsg::Info) => Self::MainMenu.goto(),
            (Self::MainMenu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => {
                Self::MainMenuCancel.swipe_left()
            }
            (Self::AccountInfo, FlowMsg::Cancelled) => Self::MainMenu.swipe_right(),
            (Self::MainMenuCancel, FlowMsg::Cancelled) => Self::MainMenu.swipe_right(),
            (Self::AddressInfo, FlowMsg::Info) => Self::MainMenu.goto(),
            (Self::Summary, FlowMsg::Info) => Self::SummaryMenu.goto(),
            (Self::SummaryMenu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => {
                Self::SummaryMenuCancel.swipe_left()
            }
            (Self::SummaryMenuCancel, FlowMsg::Cancelled) => Self::SummaryMenu.swipe_right(),
            (Self::Hold, FlowMsg::Info) => Self::HoldMenu.goto(),
            (Self::HoldMenu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => {
                Self::HoldMenuCancel.swipe_left()
            }
            (Self::HoldMenuCancel, FlowMsg::Cancelled) => Self::HoldMenu.swipe_right(),
            (Self::SummaryMenu, FlowMsg::Choice(MENU_ITEM_FEE_INFO)) => Self::FeeInfo.swipe_left(),
            (Self::MainMenu, FlowMsg::Choice(MENU_ITEM_ADDRESS_INFO)) => {
                Self::AddressInfo.swipe_left()
            }
            (Self::MainMenu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => {
                Self::AccountInfo.swipe_left()
            }
            (Self::MainMenu, FlowMsg::Cancelled) => Self::Main.swipe_right(),
            (Self::SummaryMenu, FlowMsg::Cancelled) => Self::Summary.swipe_right(),
            (Self::FeeInfo, FlowMsg::Cancelled) => Self::SummaryMenu.swipe_right(),
            (Self::HoldMenu, FlowMsg::Cancelled) => Self::Hold.swipe_right(),
            (
                Self::MainMenuCancel | Self::SummaryMenuCancel | Self::HoldMenuCancel,
                FlowMsg::Confirmed,
            ) => self.return_msg(FlowMsg::Cancelled),
            (Self::Main, FlowMsg::Cancelled) => Self::MainMenu.goto(),
            (Self::Summary, FlowMsg::Cancelled) => Self::SummaryMenu.goto(),
            (Self::Hold, FlowMsg::Cancelled) => Self::HoldMenu.goto(),
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
    .with_swipe(Direction::Down, SwipeSettings::default())
    .with_swipe(Direction::Left, SwipeSettings::default())
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
    let subtitle: Option<TString> = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into_option()?;

    let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
    let account_path: Option<TString> =
        kwargs.get(Qstr::MP_QSTR_account_path)?.try_into_option()?;

    let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;
    let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;

    let message: Obj = kwargs.get(Qstr::MP_QSTR_message)?;
    let amount: Option<Obj> = kwargs.get(Qstr::MP_QSTR_amount)?.try_into_option()?;

    let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
    let text_mono: bool = kwargs.get_or(Qstr::MP_QSTR_text_mono, true)?;

    let address: Option<Obj> = kwargs.get(Qstr::MP_QSTR_address)?.try_into_option()?;
    let address_title: Option<TString> =
        kwargs.get(Qstr::MP_QSTR_address_title)?.try_into_option()?;

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

    // Main
    let main_content = ConfirmBlobParams::new(title.unwrap_or(TString::empty()), message, None)
        .with_subtitle(subtitle)
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_chunkify(chunkify)
        .with_text_mono(text_mono)
        .with_swipe_up()
        .into_layout()?
        .one_button_request(ButtonRequest::from_num(br_code, br_name));

    // MainMenu
    let mut main_menu = VerticalMenu::empty();
    let mut main_menu_items = Vec::<usize, 3>::new();
    if address.is_some() {
        main_menu = main_menu.item(
            theme::ICON_CHEVRON_RIGHT,
            address_title.unwrap_or(TR::words__address.into()),
        );
        unwrap!(main_menu_items.push(MENU_ITEM_ADDRESS_INFO));
    }
    if account.is_some() && account_path.is_some() {
        main_menu = main_menu.item(
            theme::ICON_CHEVRON_RIGHT,
            TR::address_details__account_info.into(),
        );
        unwrap!(main_menu_items.push(MENU_ITEM_ACCOUNT_INFO));
    }
    main_menu = main_menu.danger(
        theme::ICON_CANCEL,
        cancel_text.unwrap_or(TR::send__cancel_sign.into()),
    );
    unwrap!(main_menu_items.push(MENU_ITEM_CANCEL));
    let content_main_menu = Frame::left_aligned(TString::empty(), main_menu)
        .with_cancel_button()
        .with_swipe(Direction::Right, SwipeSettings::immediate())
        .map(move |msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => {
                let selected_item = main_menu_items[i];
                Some(FlowMsg::Choice(selected_item))
            }
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

    // AccountInfo
    let ac = AddressDetails::new(TR::send__send_from.into(), account, account_path)?;
    let account_content = ac.map(|_| Some(FlowMsg::Cancelled));

    let res = if amount.is_some() {
        let content_amount =
            ConfirmBlobParams::new(TR::words__amount.into(), amount.unwrap(), None)
                .with_subtitle(subtitle)
                .with_menu_button()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_text_mono(text_mono)
                .with_swipe_up()
                .with_swipe_down()
                .into_layout()?
                .one_button_request(ButtonRequest::from_num(br_code, br_name));

        SwipeFlow::new(&ConfirmOutputWithAmount::Address)?
            .with_page(&ConfirmOutputWithAmount::Address, main_content)?
            .with_page(&ConfirmOutputWithAmount::Amount, content_amount)?
            .with_page(&ConfirmOutputWithAmount::Menu, content_main_menu)?
            .with_page(&ConfirmOutputWithAmount::AccountInfo, account_content)?
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
        .with_swipe(Direction::Down, SwipeSettings::default())
        .with_swipe(Direction::Left, SwipeSettings::default())
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
            .with_swipe(Direction::Right, SwipeSettings::immediate())
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
            .with_swipe(Direction::Right, SwipeSettings::immediate())
            .map(move |msg| match msg {
                FrameMsg::Content(VerticalMenuChoiceMsg::Selected(_)) => {
                    Some(FlowMsg::Choice(MENU_ITEM_CANCEL))
                }
                FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
            });

        let mut flow = SwipeFlow::new(&ConfirmOutputWithSummary::Main)?
            .with_page(&ConfirmOutputWithSummary::Main, main_content)?
            .with_page(&ConfirmOutputWithSummary::MainMenu, content_main_menu)?
            .with_page(&ConfirmOutputWithSummary::MainMenuCancel, get_cancel_page())?;
        if address.is_some() {
            let address_content = ConfirmBlobParams::new(
                address_title.unwrap_or(TR::words__address.into()),
                address.unwrap(),
                None,
            )
            .with_cancel_button()
            .with_chunkify(true)
            .with_text_mono(true)
            .with_swipe_right()
            .into_layout()?;
            flow = flow.with_page(&ConfirmOutputWithSummary::AddressInfo, address_content)?;
        } else {
            // dummy page - this will never be shown since there is no menu item pointing to
            // it, but the page has to exist in the flow
            flow = flow.with_page(
                &ConfirmOutputWithSummary::AddressInfo,
                Frame::left_aligned(TString::empty(), VerticalMenu::empty())
                    .map(|_| Some(FlowMsg::Cancelled)),
            )?;
        }
        flow.with_page(&ConfirmOutputWithSummary::Summary, content_summary)?
            .with_page(&ConfirmOutputWithSummary::SummaryMenu, content_summary_menu)?
            .with_page(
                &ConfirmOutputWithSummary::SummaryMenuCancel,
                get_cancel_page(),
            )?
            .with_page(&ConfirmOutputWithSummary::FeeInfo, content_fee)?
            .with_page(&ConfirmOutputWithSummary::Hold, content_hold)?
            .with_page(&ConfirmOutputWithSummary::HoldMenu, content_hold_menu)?
            .with_page(&ConfirmOutputWithSummary::HoldMenuCancel, get_cancel_page())?
            .with_page(&ConfirmOutputWithSummary::AccountInfo, account_content)?
    } else {
        SwipeFlow::new(&ConfirmOutput::Address)?
            .with_page(&ConfirmOutput::Address, main_content)?
            .with_page(&ConfirmOutput::Menu, content_main_menu)?
            .with_page(&ConfirmOutput::AccountInfo, account_content)?
            .with_page(&ConfirmOutput::CancelTap, get_cancel_page())?
    };

    Ok(LayoutObj::new(res)?.into())
}
