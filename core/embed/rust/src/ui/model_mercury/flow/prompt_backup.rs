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

use super::super::{
    component::{
        CancelInfoConfirmMsg, Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum PromptBackup {
    Intro,
    Menu,
    SkipBackupIntro,
    SkipBackupConfirm,
}

impl FlowState for PromptBackup {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (PromptBackup::Intro, SwipeDirection::Left) => {
                Decision::Goto(PromptBackup::Menu, direction)
            }
            (PromptBackup::SkipBackupIntro, SwipeDirection::Up) => {
                Decision::Goto(PromptBackup::SkipBackupConfirm, direction)
            }
            (PromptBackup::SkipBackupConfirm, SwipeDirection::Down) => {
                Decision::Goto(PromptBackup::SkipBackupIntro, direction)
            }
            (PromptBackup::Intro, SwipeDirection::Up) => Decision::Return(FlowMsg::Confirmed),
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (PromptBackup::Intro, FlowMsg::Info) => {
                Decision::Goto(PromptBackup::Menu, SwipeDirection::Left)
            }
            (PromptBackup::Menu, FlowMsg::Choice(0)) => {
                Decision::Goto(PromptBackup::SkipBackupIntro, SwipeDirection::Left)
            }
            (PromptBackup::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(PromptBackup::Intro, SwipeDirection::Right)
            }
            (PromptBackup::SkipBackupIntro, FlowMsg::Cancelled) => {
                Decision::Goto(PromptBackup::Menu, SwipeDirection::Right)
            }
            (PromptBackup::SkipBackupConfirm, FlowMsg::Cancelled) => {
                Decision::Goto(PromptBackup::SkipBackupIntro, SwipeDirection::Right)
            }
            (PromptBackup::SkipBackupConfirm, FlowMsg::Confirmed) => {
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

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_prompt_backup(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, PromptBackup::new_obj) }
}

impl PromptBackup {
    fn new_obj(_args: &[Obj], _kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = TR::backup__title_create_wallet_backup.into();
        let par_array: [Paragraph<'static>; 1] = [Paragraph::new(
            &theme::TEXT_MAIN_GREY_LIGHT,
            // FIXME: should be "contains X words" but the mnemonic/shares are not yet generated at
            // this point. We might need to merge the PromptBackup and ShowShareWords flows
            TString::from_str("Your wallet backup contains words in a specific order."),
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
            VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::backup__title_skip.into()),
        )
        .with_cancel_button()
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            FrameMsg::Button(_) => None,
        });

        let par_array_skip_intro: [Paragraph<'static>; 2] = [
            Paragraph::new(&theme::TEXT_WARNING, TR::words__not_recommended),
            Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::backup__create_backup_to_prevent_loss,
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
        .with_overlapping_content()
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
        let res = SwipeFlow::new(PromptBackup::Intro, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
