#[cfg(feature = "haptic")]
use crate::trezorhal::haptic::{play, HapticEffect};
use crate::{
    strutil::TString,
    time::Duration,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Timer},
        display::{toif::Icon, Color, Font},
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect},
        shape::{self, Renderer},
        util::split_two_lines,
    },
};

use super::super::theme;

pub enum ButtonMsg {
    Pressed,
    Released,
    Clicked,
    LongPressed,
}

pub struct Button {
    area: Rect,
    touch_expand: Option<Insets>,
    content: ButtonContent,
    content_offset: Offset,
    styles: ButtonStyleSheet,
    text_align: Alignment,
    radius: Option<u8>,
    state: State,
    long_press: Option<Duration>,
    long_timer: Timer,
    haptic: bool,
}

impl Button {
    const LINE_SPACING: i16 = 7;
    #[cfg(not(feature = "bootloader"))]
    const SUBTEXT_STYLE: TextStyle = theme::label_menu_item_subtitle();
    #[cfg(feature = "bootloader")]
    const SUBTEXT_STYLE: TextStyle = theme::TEXT_NORMAL;

    pub const fn new(content: ButtonContent) -> Self {
        Self {
            content,
            content_offset: Offset::zero(),
            area: Rect::zero(),
            touch_expand: None,
            styles: theme::button_default(),
            text_align: Alignment::Center,
            radius: None,
            state: State::Initial,
            long_press: None,
            long_timer: Timer::new(),
            haptic: true,
        }
    }

    pub const fn with_text(text: TString<'static>) -> Self {
        Self::new(ButtonContent::Text(text))
    }

    pub const fn with_text_and_subtext(text: TString<'static>, subtext: TString<'static>) -> Self {
        Self::new(ButtonContent::TextAndSubtext(text, subtext))
    }

    pub const fn with_icon(icon: Icon) -> Self {
        Self::new(ButtonContent::Icon(icon))
    }

    pub const fn with_icon_and_text(content: IconText) -> Self {
        Self::new(ButtonContent::IconAndText(content))
    }

    #[cfg(feature = "micropython")]
    pub const fn with_homebar_content(text: Option<TString<'static>>) -> Self {
        Self::new(ButtonContent::HomeBar(text))
    }

    pub const fn empty() -> Self {
        Self::new(ButtonContent::Empty)
    }

    pub const fn styled(mut self, styles: ButtonStyleSheet) -> Self {
        self.styles = styles;
        self
    }

    pub const fn with_text_align(mut self, align: Alignment) -> Self {
        self.text_align = align;
        self
    }

    pub const fn with_content_offset(mut self, offset: Offset) -> Self {
        self.content_offset = offset;
        self
    }

    pub const fn with_expanded_touch_area(mut self, expand: Insets) -> Self {
        self.touch_expand = Some(expand);
        self
    }

    pub fn with_long_press(mut self, duration: Duration) -> Self {
        self.long_press = Some(duration);
        self
    }

    pub fn with_radius(mut self, radius: u8) -> Self {
        self.radius = Some(radius);
        self
    }

    pub fn without_haptics(mut self) -> Self {
        self.haptic = false;
        self
    }

    pub fn enable_if(&mut self, ctx: &mut EventCtx, enabled: bool) {
        if enabled {
            self.enable(ctx);
        } else {
            self.disable(ctx);
        }
    }

    pub fn initially_enabled(mut self, enabled: bool) -> Self {
        if !enabled {
            self.state = State::Disabled;
        }
        self
    }

    pub fn enable(&mut self, ctx: &mut EventCtx) {
        self.set(ctx, State::Initial)
    }

    pub fn disable(&mut self, ctx: &mut EventCtx) {
        self.set(ctx, State::Disabled)
    }

    pub fn is_enabled(&self) -> bool {
        matches!(
            self.state,
            State::Initial | State::Pressed | State::Released
        )
    }

    pub fn is_pressed(&self) -> bool {
        matches!(self.state, State::Pressed)
    }

    pub fn long_press(&self) -> Option<Duration> {
        self.long_press
    }

    pub fn is_disabled(&self) -> bool {
        matches!(self.state, State::Disabled)
    }

    pub fn set_content(&mut self, content: ButtonContent) {
        if self.content != content {
            self.content = content
        }
    }

    pub fn set_expanded_touch_area(&mut self, expand: Insets) {
        self.touch_expand = Some(expand);
    }

    pub fn content(&self) -> &ButtonContent {
        &self.content
    }

    pub fn content_offset(&self) -> Offset {
        self.content_offset
    }

    pub fn content_height(&self) -> i16 {
        match &self.content {
            ButtonContent::Empty => 0,
            ButtonContent::Text(_) => self.style().font.allcase_text_height(),
            ButtonContent::Icon(icon) => icon.toif.height(),
            ButtonContent::IconAndText(child) => {
                let text_height = self.style().font.allcase_text_height();
                let icon_height = child.icon.toif.height();
                text_height.max(icon_height)
            }
            ButtonContent::TextAndSubtext(_, _) => {
                self.style().font.allcase_text_height()
                    + Self::LINE_SPACING
                    + Self::SUBTEXT_STYLE.text_font.allcase_text_height()
            }
            #[cfg(feature = "micropython")]
            ButtonContent::HomeBar(_) => theme::ACTION_BAR_HEIGHT,
        }
    }

    pub fn set_stylesheet(&mut self, styles: ButtonStyleSheet) {
        if self.styles != styles {
            self.styles = styles;
        }
    }

    pub fn style(&self) -> &ButtonStyle {
        match self.state {
            State::Initial | State::Released => self.styles.normal,
            State::Pressed => self.styles.active,
            State::Disabled => self.styles.disabled,
        }
    }

    pub fn style_sheet(&self) -> &ButtonStyleSheet {
        &self.styles
    }

    pub fn area(&self) -> Rect {
        self.area
    }

    fn set(&mut self, ctx: &mut EventCtx, state: State) {
        if self.state != state {
            self.state = state;
            ctx.request_paint();
        }
    }

    pub fn render_background<'s>(
        &self,
        target: &mut impl Renderer<'s>,
        style: &ButtonStyle,
        alpha: u8,
    ) {
        if self.radius.is_some() {
            shape::Bar::new(self.area)
                .with_bg(style.background_color)
                .with_radius(self.radius.unwrap() as i16)
                .with_thickness(2)
                .with_fg(style.button_color)
                .with_alpha(alpha)
                .render(target);
        } else {
            shape::Bar::new(self.area)
                .with_bg(style.button_color)
                .with_fg(style.button_color)
                .with_alpha(alpha)
                .render(target);
        }
    }

    pub fn render_content<'s>(
        &self,
        target: &mut impl Renderer<'s>,
        style: &ButtonStyle,
        alpha: u8,
    ) {
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text(text) => {
                let y_offset = Offset::y(self.content_height() / 2);
                let start_of_baseline = match self.text_align {
                    Alignment::Start => self.area.left_center() + self.content_offset,
                    Alignment::Center => self.area.center() + self.content_offset,
                    Alignment::End => self.area.right_center() - self.content_offset,
                } + y_offset;
                text.map(|text| {
                    shape::Text::new(start_of_baseline, text, style.font)
                        .with_fg(style.text_color)
                        .with_align(self.text_align)
                        .with_alpha(alpha)
                        .render(target);
                });
            }
            ButtonContent::TextAndSubtext(text, subtext) => {
                let text_y_offset =
                    Offset::y(self.content_height() / 2 - self.style().font.allcase_text_height());
                let subtext_y_offset = Offset::y(self.content_height() / 2);
                let start_of_baseline = match self.text_align {
                    Alignment::Start => self.area.left_center() + self.content_offset,
                    Alignment::Center => self.area.center() + self.content_offset,
                    Alignment::End => self.area.right_center() - self.content_offset,
                };
                let text_baseline = start_of_baseline - text_y_offset;
                let subtext_baseline = start_of_baseline + subtext_y_offset;

                text.map(|text| {
                    shape::Text::new(text_baseline, text, style.font)
                        .with_fg(style.text_color)
                        .with_align(self.text_align)
                        .with_alpha(alpha)
                        .render(target);
                });

                subtext.map(|subtext| {
                    shape::Text::new(subtext_baseline, subtext, Self::SUBTEXT_STYLE.text_font)
                        .with_fg(Self::SUBTEXT_STYLE.text_color)
                        .with_align(self.text_align)
                        .with_alpha(alpha)
                        .render(target);
                });
            }
            ButtonContent::Icon(icon) => {
                shape::ToifImage::new(self.area.center() + self.content_offset, icon.toif)
                    .with_align(Alignment2D::CENTER)
                    .with_fg(style.icon_color)
                    .with_alpha(alpha)
                    .render(target);
            }
            ButtonContent::IconAndText(child) => {
                child.render(target, self.area, self.style(), self.content_offset, alpha);
            }
            #[cfg(feature = "micropython")]
            ButtonContent::HomeBar(text) => {
                let baseline = self.area.center();
                if let Some(text) = text {
                    const OFFSET_Y: Offset = Offset::y(25);
                    text.map(|text| {
                        shape::Text::new(baseline, text, style.font)
                            .with_fg(style.text_color)
                            .with_align(Alignment::Center)
                            .with_alpha(alpha)
                            .render(target);
                    });
                    shape::ToifImage::new(
                        self.area.center() + OFFSET_Y,
                        theme::ICON_DASH_HORIZONTAL.toif,
                    )
                    .with_fg(style.icon_color)
                    .with_align(Alignment2D::CENTER)
                    .render(target);
                } else {
                    // double dash icon in the middle
                    const OFFSET_Y: Offset = Offset::y(5);
                    shape::ToifImage::new(baseline - OFFSET_Y, theme::ICON_DASH_HORIZONTAL.toif)
                        .with_fg(theme::GREY_LIGHT)
                        .with_align(Alignment2D::CENTER)
                        .render(target);

                    shape::ToifImage::new(baseline + OFFSET_Y, theme::ICON_DASH_HORIZONTAL.toif)
                        .with_fg(theme::GREY_LIGHT)
                        .with_align(Alignment2D::CENTER)
                        .render(target);
                }
            }
        }
    }

    pub fn render_with_alpha<'s>(&self, target: &mut impl Renderer<'s>, alpha: u8) {
        let style = self.style();
        self.render_background(target, style, alpha);
        self.render_content(target, style, alpha);
    }
}

impl Component for Button {
    type Msg = ButtonMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let touch_area = if let Some(expand) = self.touch_expand {
            self.area.outset(expand)
        } else {
            self.area
        };

        match event {
            Event::Touch(TouchEvent::TouchStart(pos)) => {
                match self.state {
                    State::Disabled => {
                        // Do nothing.
                    }
                    _ => {
                        // Touch started in our area, transform to `Pressed` state.
                        if touch_area.contains(pos) {
                            #[cfg(feature = "haptic")]
                            if self.haptic {
                                play(HapticEffect::ButtonPress);
                            }
                            self.set(ctx, State::Pressed);
                            if let Some(duration) = self.long_press {
                                self.long_timer.start(ctx, duration);
                            }
                            return Some(ButtonMsg::Pressed);
                        }
                    }
                }
            }
            Event::Touch(TouchEvent::TouchMove(pos)) => {
                match self.state {
                    State::Pressed if !touch_area.contains(pos) => {
                        // Touch is leaving our area, transform to `Released` state.
                        self.set(ctx, State::Released);
                        return Some(ButtonMsg::Released);
                    }
                    _ => {
                        // Do nothing.
                    }
                }
            }
            Event::Touch(TouchEvent::TouchEnd(pos)) => {
                match self.state {
                    State::Initial | State::Disabled => {
                        // Do nothing.
                    }
                    State::Pressed if touch_area.contains(pos) => {
                        // Touch finished in our area, we got clicked.
                        self.set(ctx, State::Initial);
                        return Some(ButtonMsg::Clicked);
                    }
                    State::Pressed => {
                        // Touch finished outside our area.
                        self.set(ctx, State::Initial);
                        self.long_timer.stop();
                        return Some(ButtonMsg::Released);
                    }
                    _ => {
                        // Touch finished outside our area.
                        self.set(ctx, State::Initial);
                        self.long_timer.stop();
                    }
                }
            }
            Event::Swipe(_) => {
                // When a swipe is detected, abort any ongoing touch.
                match self.state {
                    State::Initial | State::Disabled => {
                        // Do nothing.
                    }
                    State::Pressed => {
                        // Touch aborted
                        self.set(ctx, State::Initial);
                        self.long_timer.stop();
                        return Some(ButtonMsg::Released);
                    }
                    _ => {
                        // Irrelevant touch abort
                        self.set(ctx, State::Initial);
                        self.long_timer.stop();
                    }
                }
            }

            Event::Timer(_) if self.long_timer.expire(event) => {
                if matches!(self.state, State::Pressed) {
                    #[cfg(feature = "haptic")]
                    if self.haptic {
                        play(HapticEffect::ButtonPress);
                    }
                    self.set(ctx, State::Initial);
                    return Some(ButtonMsg::LongPressed);
                }
            }
            _ => {}
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let style = self.style();
        self.render_background(target, style, 0xFF);
        self.render_content(target, style, 0xFF);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Button {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Button");
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text(text) => t.string("text", *text),
            ButtonContent::Icon(_) => t.bool("icon", true),
            ButtonContent::IconAndText(content) => {
                t.string("text", content.text);
                t.bool("icon", true);
            }
            ButtonContent::TextAndSubtext(text, _) => {
                t.string("text", *text);
            }
            #[cfg(feature = "micropython")]
            ButtonContent::HomeBar(text) => t.string("text", text.unwrap_or(TString::empty())),
        }
    }
}

#[derive(PartialEq, Eq, Clone)]
enum State {
    Initial,
    Pressed,
    Released,
    Disabled,
}

#[derive(PartialEq, Eq, Clone)]
pub enum ButtonContent {
    Empty,
    Text(TString<'static>),
    TextAndSubtext(TString<'static>, TString<'static>),
    Icon(Icon),
    IconAndText(IconText),
    #[cfg(feature = "micropython")]
    HomeBar(Option<TString<'static>>),
}

#[derive(PartialEq, Eq, Clone, Copy)]
pub struct ButtonStyleSheet {
    pub normal: &'static ButtonStyle,
    pub active: &'static ButtonStyle,
    pub disabled: &'static ButtonStyle,
}

#[derive(PartialEq, Eq, Clone)]
pub struct ButtonStyle {
    pub font: Font,
    pub text_color: Color,
    pub button_color: Color,
    pub icon_color: Color,
    pub background_color: Color,
}

#[derive(PartialEq, Eq, Clone)]
pub struct IconText {
    text: TString<'static>,
    icon: Icon,
}

impl IconText {
    const ICON_SPACE: i16 = 46;
    const ICON_MARGIN: i16 = 4;
    const TEXT_MARGIN: i16 = 6;

    pub fn new(text: impl Into<TString<'static>>, icon: Icon) -> Self {
        Self {
            text: text.into(),
            icon,
        }
    }

    pub fn render<'s>(
        &self,
        target: &mut impl Renderer<'s>,
        area: Rect,
        style: &ButtonStyle,
        baseline_offset: Offset,
        alpha: u8,
    ) {
        let mut show_text = |text: &str, rect: Rect| {
            let text_pos = rect.left_center() + baseline_offset;
            let text_pos = Point::new(rect.top_left().x + Self::ICON_SPACE, text_pos.y);
            shape::Text::new(text_pos, text, style.font)
                .with_fg(style.text_color)
                .with_alpha(alpha)
                .render(target)
        };

        self.text.map(|t| {
            let (t1, t2) = split_two_lines(
                t,
                style.font,
                area.width() - Self::ICON_SPACE - Self::TEXT_MARGIN,
            );

            if t1.is_empty() || t2.is_empty() {
                show_text(t, area);
            } else {
                show_text(t1, Rect::new(area.top_left(), area.right_center()));
                show_text(t2, Rect::new(area.left_center(), area.bottom_right()));
            }
        });

        let icon_pos = Point::new(
            area.top_left().x + ((Self::ICON_SPACE + Self::ICON_MARGIN) / 2),
            area.center().y,
        );
        shape::ToifImage::new(icon_pos, self.icon.toif)
            .with_align(Alignment2D::CENTER)
            .with_fg(style.icon_color)
            .with_alpha(alpha)
            .render(target);
    }
}
