use crate::{
    error,
    ui::{
        component::{
            image::BlendedImage,
            text::paragraphs::{Paragraph, Paragraphs},
            Qr, Timeout,
        },
        flow::{
            base::Decision, flow_store, FlowMsg, FlowState, FlowStore, IgnoreSwipe, SwipeDirection,
            SwipeFlow, SwipePage,
        },
    },
};
use heapless::Vec;

use super::super::{
    component::{Frame, FrameMsg, IconDialog, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

const LONGSTRING: &'static str = "https://youtu.be/iFkEs4GNgfc?si=Jl4UZSIAYGVcLQKohttps://youtu.be/iFkEs4GNgfc?si=Jl4UZSIAYGVcLQKohttps://youtu.be/iFkEs4GNgfc?si=Jl4UZSIAYGVcLQKohttps://youtu.be/iFkEs4GNgfc?si=Jl4UZSIAYGVcLQKohttps://youtu.be/iFkEs4GNgfc?si=Jl4UZSIAYGVcLQKo";

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum GetAddress {
    Address,
    Menu,
    QrCode,
    AccountInfo,
    Cancel,
    Success,
}

impl FlowState for GetAddress {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (GetAddress::Address, SwipeDirection::Left) => {
                Decision::Goto(GetAddress::Menu, direction)
            }
            (GetAddress::Address, SwipeDirection::Up) => {
                Decision::Goto(GetAddress::Success, direction)
            }
            (GetAddress::Menu, SwipeDirection::Right) => {
                Decision::Goto(GetAddress::Address, direction)
            }
            (GetAddress::QrCode, SwipeDirection::Right) => {
                Decision::Goto(GetAddress::Menu, direction)
            }
            (GetAddress::AccountInfo, SwipeDirection::Right) => {
                Decision::Goto(GetAddress::Menu, direction)
            }
            (GetAddress::Cancel, SwipeDirection::Up) => Decision::Return(FlowMsg::Cancelled),
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (GetAddress::Address, FlowMsg::Info) => {
                Decision::Goto(GetAddress::Menu, SwipeDirection::Left)
            }

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

            (GetAddress::Success, _) => Decision::Return(FlowMsg::Confirmed),
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{buffer::StrBuffer, map::Map, obj::Obj, util},
    ui::layout::obj::LayoutObj,
};

pub extern "C" fn new_get_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, GetAddress::new) }
}

impl GetAddress {
    fn new(_args: &[Obj], _kwargs: &Map) -> Result<Obj, error::Error> {
        let store = flow_store()
            .add(
                Frame::left_aligned(
                    "Receive".into(),
                    SwipePage::vertical(Paragraphs::new(Paragraph::new(
                        &theme::TEXT_MONO,
                        StrBuffer::from(LONGSTRING),
                    ))),
                )
                .with_subtitle("address".into())
                .with_menu_button(),
                |msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info),
            )?
            .add(
                Frame::left_aligned(
                    "".into(),
                    VerticalMenu::context_menu(unwrap!(Vec::from_slice(&[
                        ("Address QR code", theme::ICON_QR_CODE),
                        ("Account info", theme::ICON_CHEVRON_RIGHT),
                        ("Cancel trans.", theme::ICON_CANCEL),
                    ]))),
                )
                .with_cancel_button(),
                |msg| match msg {
                    FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => {
                        Some(FlowMsg::Choice(i))
                    }
                    FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
                },
            )?
            .add(
                Frame::left_aligned(
                    "Receive address".into(),
                    IgnoreSwipe::new(Qr::new(
                        "https://youtu.be/iFkEs4GNgfc?si=Jl4UZSIAYGVcLQKo",
                        true,
                    )?),
                )
                .with_cancel_button(),
                |msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Cancelled),
            )?
            .add(
                Frame::left_aligned(
                    "Account info".into(),
                    SwipePage::vertical(Paragraphs::new(Paragraph::new(
                        &theme::TEXT_NORMAL,
                        StrBuffer::from("taproot xp"),
                    ))),
                )
                .with_cancel_button(),
                |msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Cancelled),
            )?
            .add(
                Frame::left_aligned(
                    "Cancel receive".into(),
                    SwipePage::vertical(Paragraphs::new(Paragraph::new(
                        &theme::TEXT_NORMAL,
                        StrBuffer::from("O rly?"),
                    ))),
                )
                .with_cancel_button(),
                |msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Cancelled),
            )?
            .add(
                IconDialog::new(
                    BlendedImage::new(
                        theme::IMAGE_BG_CIRCLE,
                        theme::IMAGE_FG_WARN,
                        theme::SUCCESS_COLOR,
                        theme::FG,
                        theme::BG,
                    ),
                    StrBuffer::from("Confirmed"),
                    Timeout::new(100),
                ),
                |_| Some(FlowMsg::Confirmed),
            )?;
        let res = SwipeFlow::new(GetAddress::Address, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
