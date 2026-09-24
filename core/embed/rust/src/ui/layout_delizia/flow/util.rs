use super::super::component::{
    Frame, Header, MoreInfoScreen, PromptMsg, SwipeContent, VerticalMenu, VerticalMenuChoiceMsg,
};
use super::super::{flow, theme};
use super::{
    ConfirmActionExtra, ConfirmActionMenuStrings, ConfirmActionOptions, ConfirmActionStrings,
};
use crate::maybe_trace::MaybeTrace;
use crate::micropython::Error;
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::component::swipe_detect::SwipeSettings;
use crate::ui::component::text::paragraphs::{
    Paragraph, ParagraphSource, ParagraphVecLong, VecExt,
};
use crate::ui::component::text::TextStyle;
use crate::ui::component::Component;
use crate::ui::flow::base::{Decision, DecisionBuilder};
use crate::ui::flow::{FlowController, FlowMsg, Swipable, SwipeFlow, SwipePage};
use crate::ui::geometry::Direction;
use crate::ui::layout::util::{ConfirmValueParams, StrOrBytes};

pub struct ConfirmValue {
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    footer_instruction: Option<TString<'static>>,
    footer_description: Option<TString<'static>>,
    value: StrOrBytes,
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
    chunkify: bool,
    text_mono: bool,
    classic_ellipsis: bool,
    cancel: bool,
    external_menu: bool,
    flow_menu: bool,
    options: ConfirmActionOptions,
}

impl ConfirmValue {
    pub fn new(
        title: TString<'static>,
        value: StrOrBytes,
        description: Option<TString<'static>>,
    ) -> Self {
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
            chunkify: false,
            text_mono: true,
            classic_ellipsis: false,
            cancel: false,
            external_menu: false,
            flow_menu: false,
            options: ConfirmActionOptions::new(),
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

    pub const fn with_external_menu(mut self, external_menu: bool) -> Self {
        self.external_menu = external_menu;
        self.with_menu_button()
    }

    pub const fn with_flow_menu(mut self, flow_menu: bool) -> Self {
        self.flow_menu = flow_menu;
        self
    }

    pub fn with_swipeup_footer(mut self, description: Option<TString<'static>>) -> Self {
        self.footer_instruction =
            Some(TString::from_translation(TR::instructions__tap_to_continue));
        self.footer_description = description;
        self.options = self.options.with_swipe_up(true);
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

    pub const fn with_classic_ellipsis(mut self, classic_ellipsis: bool) -> Self {
        self.classic_ellipsis = classic_ellipsis;
        self
    }

    pub const fn with_description_font(mut self, description_font: &'static TextStyle) -> Self {
        self.description_font = description_font;
        self
    }

    pub fn with_options(mut self, options: ConfirmActionOptions) -> Self {
        self.options = options;
        self
    }

    pub fn into_layout(
        self,
    ) -> Result<impl Component<Msg = FlowMsg> + Swipable + MaybeTrace, Error> {
        let paragraphs = ConfirmValueParams {
            description: self.description.unwrap_or("".into()),
            extra: self.extra.unwrap_or("".into()),
            value: self.value,
            font: if self.chunkify {
                &theme::TEXT_MONO_ADDRESS_CHUNKS
            } else if self.text_mono {
                if self.classic_ellipsis {
                    &theme::TEXT_MONO_WITH_CLASSIC_ELLIPSIS
                } else {
                    &theme::TEXT_MONO_DATA
                }
            } else {
                &theme::TEXT_NORMAL
            },
            description_font: self.description_font,
            extra_font: self.extra_font,
        }
        .into_paragraphs();

        let mut header = Header::left_aligned(self.title);
        if let Some(subtitle) = self.subtitle {
            header = header.with_subtitle(subtitle);
        }
        if self.menu_button {
            header = header.with_menu_button();
        }
        if self.cancel_button {
            header = header.with_cancel_button();
        }
        let page = SwipeContent::new(SwipePage::vertical(paragraphs));
        let mut frame = Frame::with_header(header, page);
        if let Some(instruction) = self.footer_instruction {
            frame = frame.with_footer(instruction, self.footer_description);
        }
        if self.flow_menu {
            frame = frame.with_flow_menu();
        }

        if self.options.swipe_up {
            frame = frame.with_swipe(Direction::Up, SwipeSettings::Default);
        }

        if self.options.swipe_down {
            frame = frame.with_swipe(Direction::Down, SwipeSettings::Default);
        }

        frame = frame.with_vertical_pages();

        Ok(frame.map_to_button_msg())
    }

    pub fn into_flow(self) -> Result<SwipeFlow, Error> {
        let paragraphs = ConfirmValueParams {
            description: self.description.unwrap_or("".into()),
            extra: self.extra.unwrap_or("".into()),
            value: self.value,
            font: if self.chunkify {
                &theme::TEXT_MONO_ADDRESS_CHUNKS
            } else if self.text_mono {
                if self.classic_ellipsis {
                    &theme::TEXT_MONO_WITH_CLASSIC_ELLIPSIS
                } else {
                    &theme::TEXT_MONO_DATA
                }
            } else {
                &theme::TEXT_NORMAL
            },
            description_font: self.description_font,
            extra_font: self.extra_font,
        }
        .into_paragraphs();

        let confirm_extra = if self.external_menu {
            ConfirmActionExtra::ExternalMenu
        } else if self.cancel {
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
            self.options,
        )
    }

    pub fn title(&self) -> TString<'static> {
        self.title
    }
}

pub type ShowInfoScreen = MoreInfoScreen<ParagraphVecLong<'static>>;

/// Simple read-only screen showing a list of key-value pairs with a close
/// button. Paginates automatically via action bar buttons when the content
/// does not fit on a single page.
#[inline(never)]
pub fn show_info_screen(
    title: TString<'static>,
    items: impl IntoIterator<Item = (TString<'static>, TString<'static>)>,
) -> ShowInfoScreen {
    let mut paragraphs = ParagraphVecLong::new();
    let mut first: bool = true;
    for (key, value) in items {
        // FIXME: padding:
        if !first {
            paragraphs.add(Paragraph::new::<TString<'static>>(
                &theme::TEXT_SUB_GREY,
                " ".into(),
            ));
        }
        first = false;
        paragraphs.add(Paragraph::new(&theme::TEXT_SUB_GREY, key).no_break());
        paragraphs.add(Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, value));
    }

    MoreInfoScreen::new(title, paragraphs.into_paragraphs())
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

enum SinglePage {
    Show,
}

impl FlowController for SinglePage {
    #[inline]
    fn index(&'static self) -> usize {
        0
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        self.return_msg(msg)
    }
}

pub fn single_page<T>(layout: T) -> Result<SwipeFlow, Error>
where
    T: Component<Msg = FlowMsg> + Swipable + MaybeTrace + 'static,
{
    let mut flow = SwipeFlow::new(&SinglePage::Show);
    flow.add_page(&SinglePage::Show, layout)?;
    Ok(flow)
}

pub fn dummy_page() -> impl Component<Msg = FlowMsg> + Swipable + MaybeTrace {
    Frame::with_header(
        Header::left_aligned(TString::empty()),
        VerticalMenu::empty(),
    )
    .map(|_| Some(FlowMsg::Cancelled))
}
