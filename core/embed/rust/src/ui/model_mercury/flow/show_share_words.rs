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
            ButtonRequestExt, ComponentExt, EventCtx,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
        layout::obj::LayoutObj,
        model_mercury::component::{InternallySwipable, InternallySwipableContent, SwipeContent},
    },
};
use heapless::Vec;

use super::super::{
    component::{Footer, Frame, FrameMsg, Header, PromptScreen, ShareWords},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ShowShareWords {
    Instruction,
    Words,
    Confirm,
    CheckBackupIntro,
}

impl FlowController for ShowShareWords {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Instruction, Direction::Up) => Self::Words.swipe(direction),
            (Self::Confirm, Direction::Down) => Self::Words.swipe(direction),
            (Self::Words, Direction::Up) => Self::Confirm.swipe(direction),
            (Self::Words, Direction::Down) => Self::Instruction.swipe(direction),
            (Self::CheckBackupIntro, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Words, FlowMsg::Cancelled) => Self::Instruction.swipe_down(),
            (Self::Words, FlowMsg::Confirmed) => Self::Confirm.swipe_up(),
            (Self::Confirm, FlowMsg::Confirmed) => Self::CheckBackupIntro.swipe_up(),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_show_share_words(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ShowShareWords::new_obj) }
}

fn header_updating_func(
    content: &InternallySwipableContent<ShareWords>,
    ctx: &mut EventCtx,
    header: &mut Header,
) {
    let (subtitle, subtitle_style) = content.inner().subtitle();
    header.update_subtitle(ctx, subtitle, Some(*subtitle_style));
}
fn footer_updating_func(
    content: &InternallySwipableContent<ShareWords>,
    ctx: &mut EventCtx,
    footer: &mut Footer,
) {
    let current_page = content.inner().current_page();
    let total_pages = content.inner().num_pages();
    footer.update_page_counter(ctx, current_page, Some(total_pages));
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
        .with_swipe(Direction::Up, SwipeSettings::default())
        .map(|msg| matches!(msg, FrameMsg::Content(_)).then_some(FlowMsg::Confirmed))
        .one_button_request(ButtonRequestCode::ResetDevice.with_name("share_words"))
        .with_pages(move |_| nwords + 2);

        let n_words = share_words_vec.len();
        let content_words = Frame::left_aligned(
            title,
            InternallySwipableContent::new(ShareWords::new(share_words_vec, subtitle)),
        )
        .with_swipe(Direction::Up, SwipeSettings::default())
        .with_swipe(Direction::Down, SwipeSettings::default())
        .with_vertical_pages()
        .with_subtitle(subtitle)
        .register_header_update_fn(header_updating_func)
        .with_footer_counter(TR::instructions__swipe_up.into(), n_words as u8)
        .register_footer_update_fn(footer_updating_func)
        .map(|_| None);

        let content_confirm = Frame::left_aligned(
            text_confirm,
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_footer(TR::instructions__hold_to_confirm.into(), None)
        .with_swipe(Direction::Down, SwipeSettings::default())
        .map(|_| Some(FlowMsg::Confirmed));

        let content_check_backup_intro = Frame::left_aligned(
            TR::reset__check_wallet_backup_title.into(),
            SwipeContent::new(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::reset__check_backup_instructions,
            ))),
        )
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(Direction::Up, SwipeSettings::default())
        .map(|_| Some(FlowMsg::Confirmed));

        let res = SwipeFlow::new(&ShowShareWords::Instruction)?
            .with_page(&ShowShareWords::Instruction, content_instruction)?
            .with_page(&ShowShareWords::Words, content_words)?
            .with_page(&ShowShareWords::Confirm, content_confirm)?
            .with_page(
                &ShowShareWords::CheckBackupIntro,
                content_check_backup_intro,
            )?;
        Ok(LayoutObj::new(res)?.into())
    }
}
