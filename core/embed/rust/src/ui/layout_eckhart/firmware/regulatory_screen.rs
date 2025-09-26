use crate::{
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeConfig,
            text::{
                layout::{LayoutFit, TextLayout},
                TextStyle,
            },
            Component, Event, EventCtx, Never, Paginate,
        },
        display::Icon,
        flow::Swipable,
        geometry::{Alignment, Alignment2D, Direction, Rect},
        shape::{Renderer, ToifImage},
        util::Pager,
    },
};

use super::super::{
    constant::SCREEN,
    firmware::{ActionBar, ActionBarMsg, Header, HeaderMsg},
    theme,
};

/// Full-screen component for rendering Regulatory certification.
pub struct RegulatoryScreen {
    header: Header,
    content: RegulatoryContent,
    action_bar: ActionBar,
}

pub enum RegulatoryMsg {
    Cancelled,
}

struct RegulatoryZone {
    name: Option<&'static str>,
    content: &'static str,
    icon1: Option<Icon>,
    icon2: Option<Icon>,
}

impl RegulatoryScreen {
    pub fn new() -> Self {
        let content = RegulatoryContent::new();
        let mut action_bar = ActionBar::new_paginate_only();
        // Set action bar page counter
        action_bar.update(content.pager());

        Self {
            header: Header::new(TR::regulatory_certification__title.into()).with_close_button(),
            content,
            action_bar,
        }
    }

    fn on_page_change(&mut self, direction: Direction) {
        // Update page based on the direction

        match direction {
            Direction::Up => {
                self.content.change_page(self.content.pager().next());
            }
            Direction::Down => {
                self.content.change_page(self.content.pager().prev());
            }
            _ => {}
        }

        // Update action bar content based on the current page
        self.action_bar.update(self.content.pager());
    }
}

impl Swipable for RegulatoryScreen {
    fn get_pager(&self) -> Pager {
        self.content.pager()
    }
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::default()
    }
}

impl Component for RegulatoryScreen {
    type Msg = RegulatoryMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (mut content_area, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);

        content_area = content_area.inset(theme::SIDE_INSETS);

        self.header.place(header_area);
        self.content.place(content_area);
        self.action_bar.place(action_bar_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(HeaderMsg::Cancelled) = self.header.event(ctx, event) {
            return Some(RegulatoryMsg::Cancelled);
        }

        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                ActionBarMsg::Prev => {
                    self.on_page_change(Direction::Down);
                }
                ActionBarMsg::Next => {
                    self.on_page_change(Direction::Up);
                }
                _ => {}
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.content.render(target);
        self.action_bar.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for RegulatoryScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("RegulatoryScreen");
        t.child("Header", &self.header);
        t.child("Content", &self.content);
        t.child("ActionBar", &self.action_bar);
        t.int("page_count", self.content.pager().total() as i64);
    }
}

/// Component showing regulatory certification information for several
/// geographical zones.
struct RegulatoryContent {
    area: Rect,
    pager: Pager,
}

impl RegulatoryContent {
    const SCREENS: usize = 9;
    const ZONES: [RegulatoryZone; RegulatoryContent::SCREENS] = [
        RegulatoryZone {
            name: Some("United States"),
            content: "FCC ID: VUI-TS7A01",
            icon1: Some(theme::ICON_FCC),
            icon2: None,
        },
        RegulatoryZone {
            name: None,
            content: "This device complies with Part 15 of the FCC Rules. Operation is subject to two conditions: (1) it may not cause harmful interference, and (2) it must accept any interference, including that which causes undesired operation.",
            icon1: None,
            icon2: None,
        },
        RegulatoryZone {
            name: Some("Canada"),
            content: "IC: 7582A-TS7A01\nCAN ICES-003(B) /\nNMB-003(B)",
            icon1: None,
            icon2: None,
        },
        RegulatoryZone {
            name: Some("Europe / UK"),
            content: "Trezor Company s.r.o.\nKundratka 2359/17a\nPrague 8, Czech Republic",
            icon1: Some(theme::ICON_EUROPE),
            icon2: None,
        },
        RegulatoryZone {
            name: Some("Australia /\nNew Zealand"),
            content: "",
            icon1: Some(theme::ICON_RCM),
            icon2: None,
        },
        RegulatoryZone {
            name: Some("Ukraine"),
            content: "",
            icon1: Some(theme::ICON_UKRAINE),
            icon2: None,
        },
        RegulatoryZone {
            name: Some("Japan"),
            content: "",
            icon1: Some(theme::ICON_JAPAN),
            icon2: Some(theme::ICON_JAPAN_2),
        },
        RegulatoryZone {
            name: Some("South Korea"),
            content: "",
            icon1: Some(theme::ICON_KOREA),
            icon2: None,
        },
        RegulatoryZone {
            name: Some("Taiwan"),
            content: "",
            icon1: Some(theme::ICON_TAIWAN),
            icon2: None,
        },
    ];

    pub fn new() -> Self {
        let pager = Pager::new(Self::SCREENS as u16);
        Self {
            area: Rect::zero(),
            pager,
        }
    }

    fn render_from_top<'s>(
        &self,
        area: Rect,
        style: TextStyle,
        align: Alignment,
        text: &str,
        spacing_after: i16,
        target: &mut impl Renderer<'s>,
    ) -> Rect {
        // Do not render empty text
        if text.is_empty() {
            return area;
        }
        // Render if it fits in the area and return the rest of the area
        let fitting = TextLayout::new(style)
            .with_align(align)
            .with_bounds(area)
            .fit_text(text);
        match fitting {
            LayoutFit::Fitting { height, .. } => {
                let (top, rest) = area.split_top(height + spacing_after);
                TextLayout::new(style)
                    .with_align(align)
                    .with_bounds(top)
                    .render_text(text, target, true);
                rest
            }
            // Text that does not fit in the area is not rendered
            _ => area,
        }
    }
}

impl Paginate for RegulatoryContent {
    fn pager(&self) -> Pager {
        self.pager
    }

    fn change_page(&mut self, to_page: u16) {
        self.pager.set_current(to_page);
    }
}

impl Component for RegulatoryContent {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let zone = &Self::ZONES[self.pager.current() as usize];
        let rest = if let Some(title) = zone.name {
            self.render_from_top(
                self.area,
                theme::TEXT_REGULAR,
                Alignment::Start,
                title,
                theme::TEXT_VERTICAL_SPACING,
                target,
            )
        } else {
            self.area
        };

        let rest = self.render_from_top(
            rest,
            theme::TEXT_MEDIUM,
            Alignment::Start,
            zone.content,
            theme::TEXT_VERTICAL_SPACING,
            target,
        );

        let rest = if let Some(icon1) = zone.icon1 {
            ToifImage::new(rest.top_left(), icon1.toif)
                .with_align(Alignment2D::TOP_LEFT)
                .with_fg(theme::GREY_LIGHT)
                .render(target);
            rest.split_top(icon1.toif.height() + theme::TEXT_VERTICAL_SPACING)
                .1
        } else {
            rest
        };

        if let Some(icon2) = zone.icon2 {
            ToifImage::new(rest.top_left(), icon2.toif)
                .with_align(Alignment2D::TOP_LEFT)
                .with_fg(theme::GREY_LIGHT)
                .render(target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for RegulatoryContent {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("RegulatoryContent");

        let current = self.pager.current();
        let zone = &RegulatoryContent::ZONES[current as usize];

        t.string("subtitle", zone.name.unwrap_or_default().into());
        t.string("content", zone.content.into());
    }
}
