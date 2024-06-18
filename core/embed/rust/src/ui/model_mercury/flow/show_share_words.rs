use crate::{
    error,
    micropython::{iter::IterBuf, map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequestCode,
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt},
            ButtonRequestExt, ComponentExt, SwipeDirection,
        },
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow},
        layout::obj::LayoutObj,
        model_mercury::component::SwipeContent,
    },
};
use heapless::Vec;

use super::super::{
    component::{Frame, FrameMsg, PromptScreen, ShareWords},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ShowShareWords {
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
        let subtitle: TString = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into()?;
        let share_words_obj: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        let share_words_vec: Vec<TString, 33> = util::iter_into_vec(share_words_obj)?;
        let description: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_description)?
            .try_into_option()?
            .and_then(|desc: TString| if desc.is_empty() { None } else { Some(desc) });
        let text_info: Obj = kwargs.get(Qstr::MP_QSTR_text_info)?;
        let text_confirm: TString = kwargs.get(Qstr::MP_QSTR_text_confirm)?.try_into()?;
        let highlight_repeated: bool = kwargs.get(Qstr::MP_QSTR_highlight_repeated)?.try_into()?;
        let nwords = share_words_vec.len();

        let mut instructions_paragraphs = ParagraphVecShort::new();
        for item in IterBuf::new().try_iterate(text_info)? {
            let text: TString = item.try_into()?;
            instructions_paragraphs.add(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, text));
        }
        let paragraphs_spacing = 8;
        let content_instruction = Frame::left_aligned(
            title,
            SwipeContent::new(
                instructions_paragraphs
                    .into_paragraphs()
                    .with_spacing(paragraphs_spacing),
            ),
        )
        .with_subtitle(TR::words__instructions.into())
        .with_footer(TR::instructions__swipe_up.into(), description)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .map(|msg| matches!(msg, FrameMsg::Content(_)).then_some(FlowMsg::Confirmed))
        .one_button_request(ButtonRequestCode::ResetDevice.with_type("share_words"))
        .with_pages(move |_| nwords + 2);

        let content_words =
            ShareWords::new(title, subtitle, share_words_vec, highlight_repeated).map(|_| None);

        let content_confirm = Frame::left_aligned(
            text_confirm,
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_footer(TR::instructions__hold_to_confirm.into(), None)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .map(|_| Some(FlowMsg::Confirmed));

        let content_check_backup_intro = Frame::left_aligned(
            TR::reset__check_wallet_backup_title.into(),
            SwipeContent::new(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::reset__check_backup_instructions,
            ))),
        )
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
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
