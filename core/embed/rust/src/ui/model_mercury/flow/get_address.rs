use crate::{
    error,
    micropython::{iter::IterBuf, qstr::Qstr},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, Paragraphs},
            ButtonRequestExt, ComponentExt, Qr, SwipeDirection,
        },
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow},
        layout::util::ConfirmBlob,
    },
};

use super::super::{
    component::{
        AddressDetails, CancelInfoConfirmMsg, Frame, FrameMsg, PromptScreen, StatusScreen,
        VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

const QR_BORDER: i16 = 4;

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum GetAddress {
    Address,
    Tap,
    Confirmed,
    Menu,
    QrCode,
    AccountInfo,
    Cancel,
    CancelTap,
}

impl FlowState for GetAddress {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (GetAddress::Address, SwipeDirection::Left) => {
                Decision::Goto(GetAddress::Menu, direction)
            }
            (GetAddress::Address, SwipeDirection::Up) => Decision::Goto(GetAddress::Tap, direction),
            (GetAddress::Tap, SwipeDirection::Down) => {
                Decision::Goto(GetAddress::Address, direction)
            }
            (GetAddress::Tap, SwipeDirection::Left) => Decision::Goto(GetAddress::Menu, direction),
            (GetAddress::Menu, SwipeDirection::Right) => {
                Decision::Goto(GetAddress::Address, direction)
            }
            (GetAddress::QrCode, SwipeDirection::Right) => {
                Decision::Goto(GetAddress::Menu, direction)
            }
            (GetAddress::AccountInfo, SwipeDirection::Right) => {
                Decision::Goto(GetAddress::Menu, SwipeDirection::Right)
            }
            (GetAddress::Cancel, SwipeDirection::Up) => {
                Decision::Goto(GetAddress::CancelTap, direction)
            }
            (GetAddress::Cancel, SwipeDirection::Right) => {
                Decision::Goto(GetAddress::Menu, direction)
            }
            (GetAddress::CancelTap, SwipeDirection::Down) => {
                Decision::Goto(GetAddress::Cancel, direction)
            }
            (GetAddress::CancelTap, SwipeDirection::Right) => {
                Decision::Goto(GetAddress::Menu, direction)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (GetAddress::Address, FlowMsg::Info) => {
                Decision::Goto(GetAddress::Menu, SwipeDirection::Left)
            }

            (GetAddress::Tap, FlowMsg::Confirmed) => {
                Decision::Goto(GetAddress::Confirmed, SwipeDirection::Up)
            }

            (GetAddress::Tap, FlowMsg::Info) => {
                Decision::Goto(GetAddress::Menu, SwipeDirection::Left)
            }

            (GetAddress::Confirmed, _) => Decision::Return(FlowMsg::Confirmed),

            (GetAddress::Menu, FlowMsg::Choice(0)) => {
                Decision::Goto(GetAddress::QrCode, SwipeDirection::Left)
            }

            (GetAddress::Menu, FlowMsg::Choice(1)) => {
                Decision::Goto(GetAddress::AccountInfo, SwipeDirection::Left)
            }

            (GetAddress::Menu, FlowMsg::Choice(2)) => {
                Decision::Goto(GetAddress::Cancel, SwipeDirection::Left)
            }

            (GetAddress::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(GetAddress::Address, SwipeDirection::Right)
            }

            (GetAddress::QrCode, FlowMsg::Cancelled) => {
                Decision::Goto(GetAddress::Menu, SwipeDirection::Right)
            }

            (GetAddress::AccountInfo, FlowMsg::Cancelled) => {
                Decision::Goto(GetAddress::Menu, SwipeDirection::Right)
            }

            (GetAddress::Cancel, FlowMsg::Cancelled) => {
                Decision::Goto(GetAddress::Menu, SwipeDirection::Right)
            }

            (GetAddress::CancelTap, FlowMsg::Confirmed) => Decision::Return(FlowMsg::Cancelled),

            (GetAddress::CancelTap, FlowMsg::Cancelled) => {
                Decision::Goto(GetAddress::Menu, SwipeDirection::Right)
            }

            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, util},
    ui::{
        component::swipe_detect::SwipeSettings, flow::SwipePage, layout::obj::LayoutObj,
        model_mercury::component::SwipeContent,
    },
};

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_get_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, GetAddress::new_obj) }
}

impl GetAddress {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let extra: Option<TString> = kwargs.get(Qstr::MP_QSTR_extra)?.try_into_option()?;
        let address: Obj = kwargs.get(Qstr::MP_QSTR_address)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let address_qr: TString = kwargs.get(Qstr::MP_QSTR_address_qr)?.try_into()?;
        let case_sensitive: bool = kwargs.get(Qstr::MP_QSTR_case_sensitive)?.try_into()?;

        let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let path: Option<TString> = kwargs.get(Qstr::MP_QSTR_path)?.try_into_option()?;
        let xpubs: Obj = kwargs.get(Qstr::MP_QSTR_xpubs)?;

        let br_type: TString = kwargs.get(Qstr::MP_QSTR_br_type)?.try_into()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;

        // Address
        let data_style = if chunkify {
            let address: TString = address.try_into()?;
            theme::get_chunkified_text_style(address.len())
        } else {
            &theme::TEXT_MONO
        };
        let paragraphs = ConfirmBlob {
            description: description.unwrap_or("".into()),
            extra: extra.unwrap_or("".into()),
            data: address.try_into()?,
            description_font: &theme::TEXT_NORMAL,
            extra_font: &theme::TEXT_DEMIBOLD,
            data_font: data_style,
        }
        .into_paragraphs();
        let content_address =
            Frame::left_aligned(title, SwipeContent::new(SwipePage::vertical(paragraphs)))
                .with_menu_button()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(SwipeDirection::Up, SwipeSettings::default())
                .with_swipe(SwipeDirection::Left, SwipeSettings::default())
                .with_vertical_pages()
                .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info))
                .one_button_request(ButtonRequest::from_num(br_code, br_type))
                // Count tap-to-confirm screen towards page count
                .with_pages(|address_pages| address_pages + 1);

        // Tap
        let content_tap =
            Frame::left_aligned(title, SwipeContent::new(PromptScreen::new_tap_to_confirm()))
                .with_footer(TR::instructions__tap_to_confirm.into(), None)
                .with_swipe(SwipeDirection::Down, SwipeSettings::default())
                .with_swipe(SwipeDirection::Left, SwipeSettings::default())
                .map(|msg| match msg {
                    FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
                    FrameMsg::Button(_) => Some(FlowMsg::Info),
                });

        let content_confirmed = Frame::left_aligned(
            TR::address__confirmed.into(),
            StatusScreen::new_success_timeout(),
        )
        .with_footer(TR::instructions__continue_in_app.into(), None)
        .map(|_| Some(FlowMsg::Confirmed));

        // Menu
        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty()
                .item(theme::ICON_QR_CODE, TR::address__qr_code.into())
                .item(
                    theme::ICON_CHEVRON_RIGHT,
                    TR::address_details__account_info.into(),
                )
                .danger(theme::ICON_CANCEL, TR::address__cancel_receive.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        // QrCode
        let content_qr = Frame::left_aligned(
            title,
            address_qr
                .map(|s| Qr::new(s, case_sensitive))?
                .with_border(QR_BORDER),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Cancelled));

        // AccountInfo
        let mut ad = AddressDetails::new(TR::address_details__account_info.into(), account, path)?;
        for i in IterBuf::new().try_iterate(xpubs)? {
            let [xtitle, text]: [TString; 2] = util::iter_into_array(i)?;
            ad.add_xpub(xtitle, text)?;
        }
        let content_account = ad.map(|_| Some(FlowMsg::Cancelled));

        // Cancel
        let content_cancel_info = Frame::left_aligned(
            TR::address__cancel_receive.into(),
            SwipeContent::new(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::address__cancel_contact_support,
            ))),
        )
        .with_cancel_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Cancelled));

        // CancelTap
        let content_cancel_tap = Frame::left_aligned(
            TR::address__cancel_receive.into(),
            PromptScreen::new_tap_to_cancel(),
        )
        .with_cancel_button()
        .with_footer(TR::instructions__tap_to_confirm.into(), None)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            _ => None,
        });

        let store = flow_store()
            .add(content_address)?
            .add(content_tap)?
            .add(content_confirmed)?
            .add(content_menu)?
            .add(content_qr)?
            .add(content_account)?
            .add(content_cancel_info)?
            .add(content_cancel_tap)?;
        let res = SwipeFlow::new(GetAddress::Address, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
