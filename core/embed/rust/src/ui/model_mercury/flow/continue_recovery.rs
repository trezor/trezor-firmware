use crate::{
    error,
    micropython::{iter::IterBuf, map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::{ButtonRequest, ButtonRequestCode},
        component::{
            button_request::ButtonRequestExt,
            swipe_detect::SwipeSettings,
            text::paragraphs::{
                Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort, VecExt,
            },
            ComponentExt, SwipeDirection,
        },
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow, SwipePage,
        },
        layout::{obj::LayoutObj, util::RecoveryType},
    },
};

use super::super::{
    component::{
        Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent, VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

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

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ContinueRecoveryBetweenSharesAdvanced {
    Main,
    Menu,
    CancelIntro,
    CancelConfirm,
    RemainingShares,
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

impl FlowState for ContinueRecoveryBetweenSharesAdvanced {
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
            (Self::RemainingShares, SwipeDirection::Right) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Main, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::RemainingShares.transit(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::CancelIntro.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Main.swipe_right(),
            (Self::CancelIntro, FlowMsg::Cancelled) => Self::Menu.transit(),
            (Self::CancelConfirm, FlowMsg::Cancelled) => Self::CancelIntro.swipe_right(),
            (Self::CancelConfirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (Self::RemainingShares, FlowMsg::Cancelled) => Self::Menu.transit(),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_continue_recovery(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, new_obj) }
}

fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
    let first_screen: bool = kwargs.get(Qstr::MP_QSTR_first_screen)?.try_into()?;
    let recovery_type: RecoveryType = kwargs.get(Qstr::MP_QSTR_recovery_type)?.try_into()?;
    let text: TString = kwargs.get(Qstr::MP_QSTR_text)?.try_into()?; // #shares entered
    let subtext: Option<TString> = kwargs.get(Qstr::MP_QSTR_subtext)?.try_into_option()?; // #shares remaining
    let pages: Option<Obj> = kwargs.get(Qstr::MP_QSTR_pages)?.try_into_option()?; // info about remaining shares

    let mut pars_show_shares = ParagraphVecLong::new();
    if let Some(pages) = pages {
        let pages_iterable: Obj = pages;
        for page in IterBuf::new().try_iterate(pages_iterable)? {
            let [title, description]: [TString; 2] = util::iter_into_array(page)?;
            pars_show_shares
                .add(Paragraph::new(&theme::TEXT_SUB_GREY, title))
                .add(Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, description).break_after());
        }
    }

    let (title, cancel_btn, cancel_title, cancel_intro) = match recovery_type {
        RecoveryType::Normal => (
            TR::recovery__title,
            TR::recovery__title_cancel_recovery,
            TR::recovery__title_cancel_recovery,
            TR::recovery__wanna_cancel_recovery,
        ),
        _ => (
            TR::recovery__title_dry_run,
            TR::recovery__cancel_dry_run,
            TR::recovery__title_cancel_dry_run,
            TR::recovery__wanna_cancel_dry_run,
        ),
    };

    let mut pars_main = ParagraphVecShort::new();
    let footer_instruction;
    let footer_description;
    if first_screen {
        pars_main.add(Paragraph::new(
            &theme::TEXT_MAIN_GREY_EXTRA_LIGHT,
            TR::recovery__enter_each_word,
        ));
        footer_instruction = TR::instructions__swipe_up.into();
        footer_description = None;
    } else {
        pars_main.add(Paragraph::new(&theme::TEXT_MAIN_GREY_EXTRA_LIGHT, text));
        if let Some(sub) = subtext {
            pars_main.add(Paragraph::new(&theme::TEXT_SUB_GREY, sub));
        }
        footer_instruction = TR::instructions__swipe_up.into();
        footer_description = Some(TR::instructions__enter_next_share.into());
    }

    let content_main =
        Frame::left_aligned(title.into(), SwipeContent::new(pars_main.into_paragraphs()))
            .with_subtitle(TR::words__instructions.into())
            .with_menu_button()
            .with_footer(footer_instruction, footer_description)
            .with_swipe(SwipeDirection::Up, SwipeSettings::default())
            .with_swipe(SwipeDirection::Left, SwipeSettings::default())
            .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info))
            .repeated_button_request(ButtonRequest::new(
                ButtonRequestCode::RecoveryHomepage,
                "recovery".into(),
            ))
            .with_pages(|_| 1);

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
                FrameMsg::Button(FlowMsg::Cancelled) => Some(FlowMsg::Cancelled),
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
        FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
        FrameMsg::Button(FlowMsg::Cancelled) => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let res = if first_screen {
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

        SwipeFlow::new(&ContinueRecoveryBeforeShares::Main)?
            .with_page(&ContinueRecoveryBeforeShares::Main, content_main)?
            .with_page(&ContinueRecoveryBeforeShares::Menu, content_menu)?
    } else if pars_show_shares.is_empty() {
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
    } else {
        let content_menu = Frame::left_aligned(
            TString::empty(),
            VerticalMenu::empty()
                .item(
                    theme::ICON_CHEVRON_RIGHT,
                    TR::recovery__title_remaining_shares.into(),
                )
                .danger(theme::ICON_CANCEL, cancel_btn.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let n_remaining_shares = pars_show_shares.len();
        let content_remaining_shares = Frame::left_aligned(
            TR::recovery__title_remaining_shares.into(),
            SwipeContent::new(SwipePage::vertical(pars_show_shares.into_paragraphs())),
        )
        .with_cancel_button()
        // .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .with_vertical_pages()
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Cancelled))
        .repeated_button_request(ButtonRequest::new(
            ButtonRequestCode::Other,
            "show_shares".into(),
        ))
        .with_pages(move |_| n_remaining_shares);

        SwipeFlow::new(&ContinueRecoveryBetweenSharesAdvanced::Main)?
            .with_page(&ContinueRecoveryBetweenSharesAdvanced::Main, content_main)?
            .with_page(&ContinueRecoveryBetweenSharesAdvanced::Menu, content_menu)?
            .with_page(
                &ContinueRecoveryBetweenSharesAdvanced::CancelIntro,
                content_cancel_intro,
            )?
            .with_page(
                &ContinueRecoveryBetweenSharesAdvanced::CancelConfirm,
                content_cancel_confirm,
            )?
            .with_page(
                &ContinueRecoveryBetweenSharesAdvanced::RemainingShares,
                content_remaining_shares,
            )?
    };
    Ok(LayoutObj::new(res)?.into())
}
