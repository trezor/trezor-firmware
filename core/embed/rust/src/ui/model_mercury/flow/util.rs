use super::super::{
    component::{Frame, FrameMsg},
    theme,
};
use crate::{
    error::Error,
    maybe_trace::MaybeTrace,
    micropython::obj::Obj,
    strutil::TString,
    ui::{
        component::{
            base::ComponentExt,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, VecExt},
            Component,
        },
        flow::{FlowMsg, Swipable, SwipePage},
        layout::util::ConfirmBlob,
    },
};
use heapless::Vec;

pub struct ConfirmBlobParams {
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    footer_instruction: Option<TString<'static>>,
    footer_description: Option<TString<'static>>,
    data: Obj,
    description: Option<TString<'static>>,
    extra: Option<TString<'static>>,
    menu_button: bool,
    chunkify: bool,
    text_mono: bool,
}

impl ConfirmBlobParams {
    pub const fn new(
        title: TString<'static>,
        data: Obj,
        description: Option<TString<'static>>,
    ) -> Self {
        Self {
            title,
            subtitle: None,
            footer_instruction: None,
            footer_description: None,
            data,
            description,
            extra: None,
            menu_button: false,
            chunkify: false,
            text_mono: true,
        }
    }

    pub const fn with_extra(mut self, extra: Option<TString<'static>>) -> Self {
        self.extra = extra;
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

    pub const fn with_footer(
        mut self,
        instruction: TString<'static>,
        description: Option<TString<'static>>,
    ) -> Self {
        self.footer_instruction = Some(instruction);
        self.footer_description = description;
        self
    }

    pub const fn with_chunkify(mut self, chunkify: bool) -> Self {
        self.chunkify = chunkify;
        self
    }

    pub const fn with_text_mono(mut self, text_mono: bool) -> Self {
        self.text_mono = text_mono;
        self
    }

    pub fn into_layout(
        self,
    ) -> Result<impl Component<Msg = FlowMsg> + Swipable + MaybeTrace, Error> {
        let paragraphs = ConfirmBlob {
            description: self.description.unwrap_or("".into()),
            extra: self.extra.unwrap_or("".into()),
            data: self.data.try_into()?,
            description_font: &theme::TEXT_NORMAL,
            extra_font: &theme::TEXT_DEMIBOLD,
            data_font: if self.chunkify {
                let data: TString = self.data.try_into()?;
                theme::get_chunkified_text_style(data.len())
            } else if self.text_mono {
                &theme::TEXT_MONO
            } else {
                &theme::TEXT_NORMAL
            },
        }
        .into_paragraphs();

        let page = SwipePage::vertical(paragraphs);
        let mut frame = Frame::left_aligned(self.title, page);
        if let Some(subtitle) = self.subtitle {
            frame = frame.with_subtitle(subtitle);
        }
        if self.menu_button {
            frame = frame.with_menu_button();
        }
        if let Some(instruction) = self.footer_instruction {
            frame = frame.with_footer(instruction, self.footer_description);
        }
        Ok(frame.map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info)))
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

    pub const fn with_footer(
        mut self,
        instruction: TString<'static>,
        description: Option<TString<'static>>,
    ) -> Self {
        self.footer_instruction = Some(instruction);
        self.footer_description = description;
        self
    }

    pub const fn with_chunkify(mut self, chunkify: bool) -> Self {
        self.chunkify = chunkify;
        self
    }

    pub fn into_layout(
        self,
    ) -> Result<impl Component<Msg = FlowMsg> + Swipable + MaybeTrace, Error> {
        let mut paragraphs = ParagraphVecShort::new();
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
            SwipePage::vertical(paragraphs.into_paragraphs()),
        );
        if let Some(subtitle) = self.subtitle {
            frame = frame.with_subtitle(subtitle);
        }
        if self.cancel_button {
            frame = frame.with_cancel_button();
        } else if self.menu_button {
            frame = frame.with_menu_button();
        }
        if let Some(instruction) = self.footer_instruction {
            frame = frame.with_footer(instruction, self.footer_description);
        }
        Ok(frame.map(move |msg| {
            matches!(msg, FrameMsg::Button(_)).then_some(if self.cancel_button {
                FlowMsg::Cancelled
            } else {
                FlowMsg::Info
            })
        }))
    }
}
