use crate::{
    error::Error,
    maybe_trace::MaybeTrace,
    micropython::obj::Obj,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::{
                paragraphs::{Paragraph, ParagraphSource, ParagraphVecLong, VecExt},
                TextStyle,
            },
            Component,
        },
        flow::{FlowMsg, Swipable, SwipeFlow, SwipePage},
        geometry::Direction,
        layout::util::{ConfirmValueParams, StrOrBytes},
    },
};
use heapless::Vec;

use super::{
    super::{
        component::{Frame, PromptMsg, SwipeContent, VerticalMenuChoiceMsg},
        flow, theme,
    },
    ConfirmActionExtra, ConfirmActionMenuStrings, ConfirmActionStrings,
};

pub struct ConfirmValue {
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    footer_instruction: Option<TString<'static>>,
    footer_description: Option<TString<'static>>,
    value: Obj,
    description: Option<TString<'static>>,
    description_font: &'static TextStyle,
    extra: Option<TString<'static>>,
    extra_font: &'static TextStyle,
    verb: Option<TString<'static>>,
    verb_cancel: TString<'static>,
    verb_info: Option<TString<'static>>,
    cancel_button: bool,
    menu_button: bool,
    prompt: bool,
    hold: bool,
    chunkify: bool,
    text_mono: bool,
    page_counter: bool,
    page_limit: Option<u16>,
    classic_ellipsis: bool,
    swipe_up: bool,
    swipe_down: bool,
    swipe_right: bool,
    frame_margin: usize,
    cancel: bool,
}

impl ConfirmValue {
    pub fn new(title: TString<'static>, value: Obj, description: Option<TString<'static>>) -> Self {
        Self {
            title,
            subtitle: None,
            footer_instruction: None,
            footer_description: None,
            value,
            description,
            description_font: &theme::TEXT_NORMAL,
            extra: None,
            extra_font: &theme::TEXT_DEMIBOLD,
            verb: None,
            verb_cancel: TR::buttons__cancel.into(),
            verb_info: None,
            cancel_button: false,
            menu_button: false,
            prompt: false,
            hold: false,
            chunkify: false,
            text_mono: true,
            page_counter: false,
            page_limit: None,
            classic_ellipsis: false,
            swipe_up: false,
            swipe_down: false,
            swipe_right: false,
            frame_margin: 0,
            cancel: false,
        }
    }

    pub const fn with_extra(mut self, extra: Option<TString<'static>>) -> Self {
        self.extra = extra;
        self
    }

    pub const fn with_extra_font(mut self, extra_font: &'static TextStyle) -> Self {
        self.extra_font = extra_font;
        self
    }

    pub const fn with_subtitle(mut self, subtitle: Option<TString<'static>>) -> Self {
        self.subtitle = subtitle;
        self
    }

    pub const fn with_menu_button(mut self) -> Self {
        self.menu_button = true;
        self
    }

    pub const fn with_cancel_button(mut self) -> Self {
        self.cancel_button = true;
        self
    }

    pub const fn with_verb(mut self, verb: Option<TString<'static>>) -> Self {
        self.verb = verb;
        self
    }

    pub fn with_verb_cancel(mut self, verb_cancel: Option<TString<'static>>) -> Self {
        self.verb_cancel = verb_cancel.unwrap_or(TR::buttons__cancel.into());
        self
    }

    pub const fn with_verb_info(mut self, verb_info: Option<TString<'static>>) -> Self {
        self.verb_info = verb_info;
        self
    }

    pub const fn with_prompt(mut self, prompt: bool) -> Self {
        self.prompt = prompt;
        self
    }

    pub const fn with_hold(mut self, hold: bool) -> Self {
        self.hold = hold;
        self
    }

    pub const fn with_swipe_up(mut self) -> Self {
        self.swipe_up = true;
        self
    }

    pub const fn with_swipe_down(mut self) -> Self {
        self.swipe_down = true;
        self
    }

    pub const fn with_swipe_right(mut self) -> Self {
        self.swipe_right = true;
        self
    }

    pub const fn with_frame_margin(mut self, frame_margin: usize) -> Self {
        self.frame_margin = frame_margin;
        self
    }

    pub const fn with_footer_description(
        mut self,
        footer_description: Option<TString<'static>>,
    ) -> Self {
        self.footer_description = footer_description;
        self
    }

    pub const fn with_cancel(mut self, cancel: bool) -> Self {
        self.cancel = cancel;
        self
    }

    pub const fn with_footer(
        mut self,
        instruction: TString<'static>,
        description: Option<TString<'static>>,
    ) -> Self {
        self.footer_instruction = Some(instruction);
        self.footer_description = description;
        self
    }

    pub const fn with_swipeup_footer(self, description: Option<TString<'static>>) -> Self {
        self.with_footer(
            TString::from_translation(TR::instructions__tap_to_continue),
            description,
        )
        .with_swipe_up()
    }

    pub const fn with_chunkify(mut self, chunkify: bool) -> Self {
        self.chunkify = chunkify;
        self
    }

    pub const fn with_text_mono(mut self, text_mono: bool) -> Self {
        self.text_mono = text_mono;
        self
    }

    pub fn with_page_counter(mut self, page_counter: bool) -> Self {
        self.page_counter = page_counter;
        self
    }

    pub const fn with_page_limit(mut self, page_limit: Option<u16>) -> Self {
        self.page_limit = page_limit;
        self
    }

    pub const fn with_classic_ellipsis(mut self, classic_ellipsis: bool) -> Self {
        self.classic_ellipsis = classic_ellipsis;
        self
    }

    pub const fn with_description_font(mut self, description_font: &'static TextStyle) -> Self {
        self.description_font = description_font;
        self
    }

    pub fn into_layout(
        self,
    ) -> Result<impl Component<Msg = FlowMsg> + Swipable + MaybeTrace, Error> {
        let paragraphs = ConfirmValueParams {
            description: self.description.unwrap_or("".into()),
            extra: self.extra.unwrap_or("".into()),
            value: if self.value != Obj::const_none() {
                self.value.try_into()?
            } else {
                StrOrBytes::Str("".into())
            },
            font: if self.chunkify {
                let value: TString = self.value.try_into()?;
                theme::get_chunkified_text_style(value.len())
            } else if self.text_mono {
                if self.classic_ellipsis {
                    &theme::TEXT_MONO_WITH_CLASSIC_ELLIPSIS
                } else {
                    &theme::TEXT_MONO
                }
            } else {
                &theme::TEXT_NORMAL
            },
            description_font: self.description_font,
            extra_font: self.extra_font,
        }
        .into_paragraphs();

        let page = SwipeContent::new(SwipePage::vertical(paragraphs));
        let mut frame = Frame::left_aligned(self.title, page);
        if let Some(subtitle) = self.subtitle {
            frame = frame.with_subtitle(subtitle);
        }
        if self.menu_button {
            frame = frame.with_menu_button();
        }
        if self.cancel_button {
            frame = frame.with_cancel_button();
        }
        if let Some(instruction) = self.footer_instruction {
            frame = frame.with_footer(instruction, self.footer_description);
            frame = frame.with_swipe(Direction::Left, SwipeSettings::default());
        }

        if self.swipe_up {
            frame = frame.with_swipe(Direction::Up, SwipeSettings::default());
        }

        if self.swipe_down {
            frame = frame.with_swipe(Direction::Down, SwipeSettings::default());
        }

        if self.swipe_right {
            frame = frame.with_swipe(Direction::Right, SwipeSettings::default());
        }

        frame = frame.with_vertical_pages();

        Ok(frame.map_to_button_msg())
    }

    pub fn into_flow(self) -> Result<SwipeFlow, Error> {
        let paragraphs = ConfirmValueParams {
            description: self.description.unwrap_or("".into()),
            extra: self.extra.unwrap_or("".into()),
            value: self.value.try_into()?,
            font: if self.chunkify {
                let value: TString = self.value.try_into()?;
                theme::get_chunkified_text_style(value.len())
            } else if self.text_mono {
                if self.classic_ellipsis {
                    &theme::TEXT_MONO_WITH_CLASSIC_ELLIPSIS
                } else {
                    &theme::TEXT_MONO
                }
            } else {
                &theme::TEXT_NORMAL
            },
            description_font: self.description_font,
            extra_font: self.extra_font,
        }
        .into_paragraphs();

        let confirm_extra = if self.cancel {
            ConfirmActionExtra::Cancel
        } else {
            ConfirmActionExtra::Menu(
                ConfirmActionMenuStrings::new()
                    .with_verb_cancel(Some(self.verb_cancel))
                    .with_verb_info(self.verb_info),
            )
        };

        flow::new_confirm_action_simple(
            paragraphs,
            confirm_extra,
            ConfirmActionStrings::new(
                self.title,
                self.subtitle,
                self.verb,
                self.prompt.then_some(self.title),
            )
            .with_footer_description(self.footer_description),
            self.hold,
            self.page_limit,
            self.frame_margin,
            self.page_counter,
        )
    }

    pub fn title(&self) -> TString<'static> {
        self.title
    }
}

pub struct ShowInfoParams {
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    menu_button: bool,
    cancel_button: bool,
    footer_instruction: Option<TString<'static>>,
    footer_description: Option<TString<'static>>,
    chunkify: bool,
    swipe_up: bool,
    swipe_down: bool,
    items: Vec<(TString<'static>, TString<'static>), 4>,
}

impl ShowInfoParams {
    pub const fn new(title: TString<'static>) -> Self {
        Self {
            title,
            subtitle: None,
            menu_button: false,
            cancel_button: false,
            footer_instruction: None,
            footer_description: None,
            chunkify: false,
            swipe_up: false,
            swipe_down: false,
            items: Vec::new(),
        }
    }

    pub fn add(mut self, key: TString<'static>, value: TString<'static>) -> Option<Self> {
        if self.items.push((key, value)).is_ok() {
            Some(self)
        } else {
            None
        }
    }

    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    #[inline(never)]
    pub const fn with_subtitle(mut self, subtitle: Option<TString<'static>>) -> Self {
        self.subtitle = subtitle;
        self
    }

    #[inline(never)]
    pub const fn with_menu_button(mut self) -> Self {
        self.menu_button = true;
        self
    }

    #[inline(never)]
    pub const fn with_cancel_button(mut self) -> Self {
        self.cancel_button = true;
        self
    }

    #[inline(never)]
    pub const fn with_footer(
        mut self,
        instruction: TString<'static>,
        description: Option<TString<'static>>,
    ) -> Self {
        self.footer_instruction = Some(instruction);
        self.footer_description = description;
        self
    }

    pub const fn with_swipeup_footer(self, description: Option<TString<'static>>) -> Self {
        self.with_footer(
            TString::from_translation(TR::instructions__tap_to_continue),
            description,
        )
        .with_swipe_up()
    }

    pub const fn with_swipe_up(mut self) -> Self {
        self.swipe_up = true;
        self
    }

    pub const fn with_swipe_down(mut self) -> Self {
        self.swipe_down = true;
        self
    }

    #[inline(never)]
    pub fn into_layout(
        self,
    ) -> Result<impl Component<Msg = FlowMsg> + Swipable + MaybeTrace, Error> {
        let mut paragraphs = ParagraphVecLong::new();
        let mut first: bool = true;
        for item in self.items {
            // FIXME: padding:
            if !first {
                paragraphs.add(Paragraph::new::<TString<'static>>(
                    &theme::TEXT_SUB_GREY,
                    " ".into(),
                ));
            }
            first = false;
            paragraphs.add(Paragraph::new(&theme::TEXT_SUB_GREY, item.0).no_break());
            if self.chunkify {
                paragraphs.add(Paragraph::new(
                    theme::get_chunkified_text_style(item.1.len()),
                    item.1,
                ));
            } else {
                paragraphs.add(Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, item.1));
            }
        }

        let mut frame = Frame::left_aligned(
            self.title,
            SwipeContent::new(SwipePage::vertical(paragraphs.into_paragraphs())),
        );
        if let Some(subtitle) = self.subtitle {
            frame = frame.with_subtitle(subtitle);
        }
        if self.cancel_button {
            frame = frame
                .with_cancel_button()
                .with_swipe(Direction::Right, SwipeSettings::immediate());
        } else if self.menu_button {
            frame = frame
                .with_menu_button()
                .with_swipe(Direction::Left, SwipeSettings::default());
        }
        if let Some(instruction) = self.footer_instruction {
            frame = frame.with_footer(instruction, self.footer_description);
        }

        if self.swipe_up {
            frame = frame.with_swipe(Direction::Up, SwipeSettings::default());
        }

        if self.swipe_down {
            frame = frame.with_swipe(Direction::Down, SwipeSettings::default());
        }

        frame = frame.with_vertical_pages();

        Ok(frame.map_to_button_msg())
    }
}

pub fn map_to_confirm(msg: PromptMsg) -> Option<FlowMsg> {
    match msg {
        PromptMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => None,
    }
}

pub fn map_to_prompt(msg: PromptMsg) -> Option<FlowMsg> {
    match msg {
        PromptMsg::Confirmed => Some(FlowMsg::Confirmed),
        PromptMsg::Cancelled => Some(FlowMsg::Cancelled),
    }
}

pub fn map_to_choice(msg: VerticalMenuChoiceMsg) -> Option<FlowMsg> {
    match msg {
        VerticalMenuChoiceMsg::Selected(i) => Some(FlowMsg::Choice(i)),
    }
}
