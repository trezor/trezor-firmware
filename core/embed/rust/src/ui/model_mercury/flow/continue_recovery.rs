use crate::{
    error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::{ButtonRequest, ButtonRequestCode},
        component::{
            button_request::ButtonRequestExt,
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt},
            ComponentExt, SwipeDirection,
        },
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow,
        },
        layout::obj::LayoutObj,
        model_mercury::component::{CancelInfoConfirmMsg, PromptScreen, SwipeContent},
    },
};

use super::super::{
    component::{Frame, FrameMsg, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

const RECOVERY_TYPE_NORMAL: u32 = 0;
const RECOVERY_TYPE_DRY_RUN: u32 = 1;
const RECOVERY_TYPE_UNLOCK_REPEATED_BACKUP: u32 = 2;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ContinueRecoveryBeforeShares {
    Main,
    Menu,
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ContinueRecoveryBetweenShares {
    Main,
    Menu,
    CancelIntro,
    CancelConfirm,
}

impl FlowState for ContinueRecoveryBeforeShares {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Main, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Menu, SwipeDirection::Right) => Self::Main.swipe(direction),
            (Self::Main, SwipeDirection::Up) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Main, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Main.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

impl FlowState for ContinueRecoveryBetweenShares {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Main, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Menu, SwipeDirection::Right) => Self::Main.swipe(direction),
            (Self::Main, SwipeDirection::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::CancelIntro, SwipeDirection::Up) => Self::CancelConfirm.swipe(direction),
            (Self::CancelIntro, SwipeDirection::Right) => Self::Menu.swipe(direction),
            (Self::CancelConfirm, SwipeDirection::Down) => Self::CancelIntro.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Main, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::CancelIntro.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Main.swipe_right(),
            (Self::CancelIntro, FlowMsg::Cancelled) => Self::Menu.transit(),
            (Self::CancelConfirm, FlowMsg::Cancelled) => Self::CancelIntro.swipe_right(),
            (Self::CancelConfirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_continue_recovery(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe {
        util::try_with_args_and_kwargs(n_args, args, kwargs, ContinueRecoveryBeforeShares::new_obj)
    }
}

impl ContinueRecoveryBeforeShares {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let first_screen: bool = kwargs.get(Qstr::MP_QSTR_first_screen)?.try_into()?;
        let recovery_type: u32 = kwargs.get(Qstr::MP_QSTR_recovery_type)?.try_into()?;
        let text: TString = kwargs.get(Qstr::MP_QSTR_text)?.try_into()?; // #shares entered
        let subtext: Option<TString> = kwargs.get(Qstr::MP_QSTR_subtext)?.try_into_option()?; // #shares remaining

        let (title, cancel_btn, cancel_title, cancel_intro) =
            if recovery_type == RECOVERY_TYPE_NORMAL {
                (
                    TR::recovery__title,
                    TR::recovery__title_cancel_recovery,
                    TR::recovery__title_cancel_recovery,
                    TR::recovery__wanna_cancel_recovery,
                )
            } else {
                // dry-run
                (
                    TR::recovery__title_dry_run,
                    TR::recovery__cancel_dry_run,
                    TR::recovery__title_cancel_dry_run,
                    TR::recovery__wanna_cancel_dry_run,
                )
            };

        let mut pars = ParagraphVecShort::new();
        let footer_instruction;
        let footer_description;
        if first_screen {
            pars.add(Paragraph::new(
                &theme::TEXT_MAIN_GREY_EXTRA_LIGHT,
                TR::recovery__enter_each_word,
            ));
            footer_instruction = TR::instructions__swipe_up.into();
            footer_description = None;
        } else {
            pars.add(Paragraph::new(&theme::TEXT_MAIN_GREY_EXTRA_LIGHT, text));
            if let Some(sub) = subtext {
                pars.add(Paragraph::new(&theme::TEXT_SUB_GREY, sub));
            }
            footer_instruction = TR::instructions__swipe_up.into();
            footer_description = Some(TR::instructions__enter_next_share.into());
        }

        let paragraphs_main = Paragraphs::new(pars);
        let content_main = Frame::left_aligned(title.into(), SwipeContent::new(paragraphs_main))
            .with_subtitle(TR::words__instructions.into())
            .with_menu_button()
            .with_footer(footer_instruction, footer_description)
            .with_swipe(SwipeDirection::Up, SwipeSettings::default())
            .with_swipe(SwipeDirection::Left, SwipeSettings::default())
            .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info))
            .repeated_button_request(ButtonRequest::new(
                ButtonRequestCode::RecoveryHomepage,
                "recovery".into(),
            ));

        let content_menu = Frame::left_aligned(
            TString::empty(),
            VerticalMenu::empty().danger(theme::ICON_CANCEL, cancel_btn.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let paragraphs_cancel = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, cancel_intro).with_bottom_padding(17),
            Paragraph::new(&theme::TEXT_WARNING, TR::recovery__progress_will_be_lost),
        ])
        .into_paragraphs();
        let content_cancel_intro =
            Frame::left_aligned(cancel_title.into(), SwipeContent::new(paragraphs_cancel))
                .with_cancel_button()
                .with_footer(
                    TR::instructions__swipe_up.into(),
                    Some(TR::words__continue_anyway.into()),
                )
                .with_swipe(SwipeDirection::Up, SwipeSettings::default())
                .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
                .map(|msg| match msg {
                    FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
                    _ => None,
                })
                .repeated_button_request(ButtonRequest::new(
                    ButtonRequestCode::ProtectCall,
                    "abort_recovery".into(),
                ));

        let content_cancel_confirm = Frame::left_aligned(
            cancel_title.into(),
            SwipeContent::new(PromptScreen::new_tap_to_cancel()),
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

        let res = if first_screen {
            SwipeFlow::new(&ContinueRecoveryBeforeShares::Main)?
                .with_page(&ContinueRecoveryBeforeShares::Main, content_main)?
                .with_page(&ContinueRecoveryBeforeShares::Menu, content_menu)?
        } else {
            SwipeFlow::new(&ContinueRecoveryBetweenShares::Main)?
                .with_page(&ContinueRecoveryBetweenShares::Main, content_main)?
                .with_page(&ContinueRecoveryBetweenShares::Menu, content_menu)?
                .with_page(
                    &ContinueRecoveryBetweenShares::CancelIntro,
                    content_cancel_intro,
                )?
                .with_page(
                    &ContinueRecoveryBetweenShares::CancelConfirm,
                    content_cancel_confirm,
                )?
        };
        Ok(LayoutObj::new(res)?.into())
    }
}
