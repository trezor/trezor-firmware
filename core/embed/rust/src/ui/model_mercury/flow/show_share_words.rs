use crate::{
    error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, Paragraphs},
            ComponentExt,
        },
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow, SwipePage},
        layout::obj::LayoutObj,
    },
};
use heapless::Vec;

use super::super::{
    component::{Frame, FrameMsg, PromptScreen, ShareWords, SwipeDirection},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ShowShareWords {
    // TODO: potentially also add there the 'never put anywhere digital' warning?
    Instruction,
    Words,
    Confirm,
    CheckBackupIntro,
}

impl FlowState for ShowShareWords {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (ShowShareWords::Instruction, SwipeDirection::Up) => {
                Decision::Goto(ShowShareWords::Words, direction)
            }
            (ShowShareWords::Confirm, SwipeDirection::Down) => {
                Decision::Goto(ShowShareWords::Words, direction)
            }
            (ShowShareWords::Words, SwipeDirection::Up) => {
                Decision::Goto(ShowShareWords::Confirm, direction)
            }
            (ShowShareWords::Words, SwipeDirection::Down) => {
                Decision::Goto(ShowShareWords::Instruction, direction)
            }
            (ShowShareWords::CheckBackupIntro, SwipeDirection::Up) => {
                Decision::Return(FlowMsg::Confirmed)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (ShowShareWords::Words, FlowMsg::Cancelled) => {
                Decision::Goto(ShowShareWords::Instruction, SwipeDirection::Down)
            }
            (ShowShareWords::Words, FlowMsg::Confirmed) => {
                Decision::Goto(ShowShareWords::Confirm, SwipeDirection::Up)
            }
            (ShowShareWords::Confirm, FlowMsg::Confirmed) => {
                Decision::Goto(ShowShareWords::CheckBackupIntro, SwipeDirection::Up)
            }
            _ => Decision::Nothing,
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_show_share_words(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ShowShareWords::new_obj) }
}

impl ShowShareWords {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let share_words_obj: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        let share_words_vec: Vec<TString, 33> = util::iter_into_vec(share_words_obj)?;
        let text_info: TString = kwargs.get(Qstr::MP_QSTR_text_info)?.try_into()?;
        let text_confirm: TString = kwargs.get(Qstr::MP_QSTR_text_confirm)?.try_into()?;

        let content_instruction = Frame::left_aligned(
            title,
            SwipePage::vertical(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                text_info,
            ))),
        )
        .with_subtitle(TR::words__instructions.into())
        .with_footer(TR::instructions__swipe_up.into(), None)
        .map(|msg| matches!(msg, FrameMsg::Content(_)).then_some(FlowMsg::Confirmed));

        let content_words =
            Frame::left_aligned(title, ShareWords::new(share_words_vec)).map(|_| None);

        let content_confirm =
            Frame::left_aligned(text_confirm, PromptScreen::new_hold_to_confirm())
                .with_footer(TR::instructions__hold_to_confirm.into(), None)
                .map(|_| Some(FlowMsg::Confirmed));

        let content_check_backup_intro = Frame::left_aligned(
            TR::reset__check_backup_title.into(),
            SwipePage::vertical(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::reset__check_backup_instructions,
            ))),
        )
        .with_subtitle(TR::words__instructions.into())
        .with_footer(TR::instructions__swipe_up.into(), None)
        .map(|_| Some(FlowMsg::Confirmed));

        let store = flow_store()
            .add(content_instruction)?
            .add(content_words)?
            .add(content_confirm)?
            .add(content_check_backup_intro)?;
        let res = SwipeFlow::new(ShowShareWords::Instruction, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
