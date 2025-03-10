use crate::ui::{
    component::{Component, Event, EventCtx, Label},
    constant::SCREEN,
    geometry::{Insets, Rect},
    layout_eckhart::theme::{ACTION_BAR_HEIGHT, SIDE_INSETS},
    shape::Renderer,
};

use super::{
    super::{
        cshape::ScreenBorder,
        theme::{HEADER_HEIGHT, TEXT_VERTICAL_SPACING},
    },
    BldActionBar, BldActionBarMsg, BldHeader, BldHeaderMsg,
};

/// Full-screen component for rendering text. Reduced variant for Bootloader UI.
///
/// The component wraps the full content of the generic page spec:
/// - Header (Optional)
/// - Label with the main text
/// - Label with the secondary text (Optional)
/// - Footer / Action bar (Optional, mutually exclusive)
pub struct BldTextScreen<'a> {
    header: Option<BldHeader<'a>>,
    label1: Label<'a>,
    label2: Option<Label<'a>>,
    action_bar: Option<BldActionBar>,
    footer: Option<Label<'a>>,
    screen_border: Option<ScreenBorder>,
    more_info: Option<MoreInfo<'a>>,
    more_info_showing: bool,
}

struct MoreInfo<'a> {
    header: BldHeader<'a>,
    text: Label<'a>,
}

#[derive(Copy, Clone, ToPrimitive)]
pub enum BldTextScreenMsg {
    Cancelled = 1,
    Confirmed = 2,
    Menu = 3,
}

impl<'a> BldTextScreen<'a> {
    pub fn new(label1: Label<'a>) -> Self {
        Self {
            header: None,
            label1,
            label2: None,
            action_bar: None,
            footer: None,
            screen_border: None,
            more_info: None,
            more_info_showing: false,
        }
    }

    pub fn with_header(mut self, header: BldHeader<'a>) -> Self {
        self.header = Some(header);
        self
    }

    pub fn with_label2(mut self, label2: Label<'a>) -> Self {
        self.label2 = Some(label2);
        self
    }

    pub fn with_action_bar(mut self, action_bar: BldActionBar) -> Self {
        self.footer = None;
        self.action_bar = Some(action_bar);
        self
    }

    pub fn with_footer(mut self, footer: Label<'a>) -> Self {
        self.action_bar = None;
        self.footer = Some(footer);
        self
    }

    pub fn with_screen_border(mut self, screen_border: ScreenBorder) -> Self {
        self.screen_border = Some(screen_border);
        self
    }

    pub fn with_more_info(mut self, header_info: BldHeader<'a>, text_info: Label<'a>) -> Self {
        self.more_info = Some(MoreInfo {
            header: header_info,
            text: text_info,
        });
        self
    }
}

impl<'a> Component for BldTextScreen<'a> {
    type Msg = BldTextScreenMsg;

    fn place(&mut self, _bounds: Rect) -> Rect {
        let (header_area, content_area) = SCREEN.split_top(HEADER_HEIGHT);
        let (content_area, action_bar_area) = content_area.split_bottom(ACTION_BAR_HEIGHT);

        let content_area = content_area.inset(SIDE_INSETS);
        let text1_height = self.label1.text_height(content_area.width());
        let text2_height = self
            .label2
            .as_ref()
            .map_or(0, |t| t.text_height(content_area.width()));
        let (text1_area, area) = content_area.split_top(text1_height);
        let (text2_area, _) = area
            .inset(Insets::top(TEXT_VERTICAL_SPACING))
            .split_top(text2_height);

        self.header.place(header_area);
        self.label1.place(text1_area);
        self.label2.place(text2_area);
        self.action_bar.place(action_bar_area);
        self.footer.place(action_bar_area);

        if let Some(more_info) = &mut self.more_info {
            more_info.header.place(header_area);
            more_info.text.place(content_area);
        }
        SCREEN
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(more_info) = &mut self.more_info {
            if self.more_info_showing {
                if let Some(BldHeaderMsg::Cancelled) = more_info.header.event(ctx, event) {
                    self.more_info_showing = false;
                    return None;
                }
            }
        }
        match self.header.event(ctx, event) {
            // FIXME: This is a hack for `screen_install_confirm` which expects `2` for the Menu
            Some(BldHeaderMsg::Menu) => return Some(BldTextScreenMsg::Cancelled),
            Some(BldHeaderMsg::Info) => {
                if !self.more_info_showing {
                    self.more_info_showing = true;
                    return None;
                }
            }
            _ => (),
        }
        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                BldActionBarMsg::Cancelled => return Some(BldTextScreenMsg::Cancelled),
                BldActionBarMsg::Confirmed => return Some(BldTextScreenMsg::Confirmed),
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.more_info_showing {
            if let Some(more_info) = &self.more_info {
                more_info.header.render(target);
                more_info.text.render(target);
            }
        } else {
            self.header.render(target);
            self.label1.render(target);
            self.label2.render(target);
            self.action_bar.render(target);
            self.footer.render(target);
        }
        if let Some(screen_border) = &self.screen_border {
            screen_border.render(u8::MAX, target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for BldTextScreen<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("BldTextScreen");
    }
}
