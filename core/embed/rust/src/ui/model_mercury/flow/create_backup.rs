use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, Paragraphs},
            ComponentExt, SwipeDirection,
        },
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow, SwipePage},
    },
};
use heapless::Vec;

use super::super::{
    component::{
        CancelInfoConfirmMsg, Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum CreateBackup {
    Intro,
    Menu,
    SkipBackupIntro,
    SkipBackupConfirm,
}

impl FlowState for CreateBackup {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (CreateBackup::Intro, SwipeDirection::Left) => {
                Decision::Goto(CreateBackup::Menu, direction)
            }
            (CreateBackup::SkipBackupIntro, SwipeDirection::Up) => {
                Decision::Goto(CreateBackup::SkipBackupConfirm, direction)
            }
            (CreateBackup::SkipBackupConfirm, SwipeDirection::Down) => {
                Decision::Goto(CreateBackup::SkipBackupIntro, direction)
            }
            (CreateBackup::Intro, SwipeDirection::Up) => Decision::Return(FlowMsg::Confirmed),
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (CreateBackup::Intro, FlowMsg::Info) => {
                Decision::Goto(CreateBackup::Menu, SwipeDirection::Left)
            }
            (CreateBackup::Menu, FlowMsg::Choice(0)) => {
                Decision::Goto(CreateBackup::SkipBackupIntro, SwipeDirection::Left)
            }
            (CreateBackup::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(CreateBackup::Intro, SwipeDirection::Right)
            }
            (CreateBackup::SkipBackupIntro, FlowMsg::Cancelled) => {
                Decision::Goto(CreateBackup::Menu, SwipeDirection::Right)
            }
            (CreateBackup::SkipBackupConfirm, FlowMsg::Cancelled) => {
                Decision::Goto(CreateBackup::SkipBackupIntro, SwipeDirection::Right)
            }
            (CreateBackup::SkipBackupConfirm, FlowMsg::Confirmed) => {
                Decision::Return(FlowMsg::Cancelled)
            }
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, util},
    ui::layout::obj::LayoutObj,
};

pub extern "C" fn new_create_backup(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, CreateBackup::new) }
}

impl CreateBackup {
    fn new(_args: &[Obj], _kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = TR::backup__title_backup_wallet.into();
        let par_array: [Paragraph<'static>; 1] = [Paragraph::new(
            &theme::TEXT_MAIN_GREY_LIGHT,
            TString::from_str("Your wallet backup contains X words in a specific order."),
        )];
        let paragraphs = Paragraphs::new(par_array);
        let content_intro = Frame::left_aligned(title, SwipePage::vertical(paragraphs))
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .map(|msg| {
                matches!(msg, FrameMsg::Button(CancelInfoConfirmMsg::Info)).then_some(FlowMsg::Info)
            });

        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::context_menu(unwrap!(Vec::from_slice(&[(
                "Skip backup", // FIXME: use TString
                theme::ICON_CANCEL
            )]))),
        )
        .with_cancel_button()
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            FrameMsg::Button(_) => None,
        });

        let par_array_skip_intro: [Paragraph<'static>; 2] = [
            Paragraph::new(&theme::TEXT_WARNING, TString::from_str("Not recommended!")),
            Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TString::from_str("Create a backup to avoid losing access to your funds"),
            ),
        ];
        let paragraphs_skip_intro = Paragraphs::new(par_array_skip_intro);
        let content_skip_intro = Frame::left_aligned(
            TR::backup__title_skip.into(),
            SwipePage::vertical(paragraphs_skip_intro),
        )
        .with_cancel_button()
        .with_footer(
            TR::instructions__swipe_up.into(),
            Some(TR::words__continue_anyway.into()),
        )
        .map(|msg| match msg {
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            _ => None,
        });

        let content_skip_confirm = Frame::left_aligned(
            TR::backup__title_skip.into(),
            PromptScreen::new_tap_to_cancel(),
        )
        .with_footer(TR::instructions__tap_to_confirm.into(), None)
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            _ => None,
        });

        let store = flow_store()
            .add(content_intro)?
            .add(content_menu)?
            .add(content_skip_intro)?
            .add(content_skip_confirm)?;
        let res = SwipeFlow::new(CreateBackup::Intro, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
