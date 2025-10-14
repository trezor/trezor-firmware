#[cfg(feature = "haptic")]
use crate::trezorhal::haptic::{play, HapticEffect};
use crate::{
    strutil::TString,
    time::ShortDuration,
    ui::{
        component::{
            text::{layout::LayoutFit, TextStyle},
            Component, Event, EventCtx, TextLayout, Timer,
        },
        display::{toif::Icon, Color, Font},
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

use super::theme;

pub enum ButtonMsg {
    Pressed,
    Released,
    Clicked,
    LongPressed,
}

pub struct Button {
    area: Rect,
    touch_expand: Insets,
    content: ButtonContent,
    stylesheet: ButtonStyleSheet,
    text_align: Alignment,
    radius: Option<u8>,
    state: State,
    long_press: ShortDuration, // long press requires non-zero duration
    long_timer: Timer,
    haptic: bool,
}

impl Button {
    /// Offsets the baseline of the button text
    /// -x/+x => left/right
    /// -y/+y => up/down
    pub const BASELINE_OFFSET: Offset = Offset::new(2, 6);

    pub const fn new(content: ButtonContent) -> Self {
        Self {
            content,
            area: Rect::zero(),
            touch_expand: Insets::zero(),
            stylesheet: theme::button_default(),
            text_align: Alignment::Start,
            radius: None,
            state: State::Initial,
            long_press: ShortDuration::ZERO,
            long_timer: Timer::new(),
            haptic: true,
        }
    }

    pub const fn with_text(text: TString<'static>) -> Self {
        Self::new(ButtonContent::Text(text))
    }

    pub const fn with_icon(icon: Icon) -> Self {
        Self::new(ButtonContent::Icon(icon))
    }

    pub const fn with_icon_and_text(content: IconText) -> Self {
        Self::new(ButtonContent::IconAndText(content))
    }

    pub const fn empty() -> Self {
        Self::new(ButtonContent::Empty)
    }

    pub const fn styled(mut self, stylesheet: ButtonStyleSheet) -> Self {
        self.stylesheet = stylesheet;
        self
    }

    pub const fn with_text_align(mut self, align: Alignment) -> Self {
        self.text_align = align;
        self
    }

    pub const fn with_expanded_touch_area(mut self, expand: Insets) -> Self {
        self.touch_expand = expand;
        self
    }

    pub fn with_long_press(mut self, duration: ShortDuration) -> Self {
        debug_assert_ne!(duration, ShortDuration::ZERO);
        self.long_press = duration;
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

    pub fn is_disabled(&self) -> bool {
        matches!(self.state, State::Disabled)
    }

    pub fn set_content(&mut self, content: ButtonContent) {
        if self.content != content {
            self.content = content
        }
    }

    pub fn content(&self) -> &ButtonContent {
        &self.content
    }

    pub fn set_stylesheet(&mut self, ctx: &mut EventCtx, stylesheet: ButtonStyleSheet) {
        if self.stylesheet != stylesheet {
            self.stylesheet = stylesheet;
            ctx.request_paint();
        }
    }

    pub fn button_style(&self) -> &ButtonStyle {
        match self.state {
            State::Initial | State::Released => self.stylesheet.normal,
            State::Pressed => self.stylesheet.active,
            State::Disabled => self.stylesheet.disabled,
        }
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
                let y_offset = Offset::y(self.button_style().font.text_height() / 2);
                let start_of_baseline = match self.text_align {
                    Alignment::Start => {
                        self.area.left_center() + Offset::x(Self::BASELINE_OFFSET.x)
                    }
                    Alignment::Center => self.area.center(),
                    Alignment::End => self.area.right_center() - Offset::x(Self::BASELINE_OFFSET.x),
                } + y_offset;
                text.map(|text| {
                    shape::Text::new(start_of_baseline, text, style.font)
                        .with_fg(style.text_color)
                        .with_align(self.text_align)
                        .with_alpha(alpha)
                        .render(target);
                });
            }
            ButtonContent::Icon(icon) => {
                shape::ToifImage::new(self.area.center(), icon.toif)
                    .with_align(Alignment2D::CENTER)
                    .with_fg(style.icon_color)
                    .with_alpha(alpha)
                    .render(target);
            }
            ButtonContent::IconAndText(child) => {
                child.render(target, self.area, self.button_style(), alpha);
            }
        }
    }

    pub fn render_with_alpha<'s>(&self, target: &mut impl Renderer<'s>, alpha: u8) {
        let style = self.button_style();
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
        let touch_area = self.area.outset(self.touch_expand);

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
                            if self.long_press != ShortDuration::ZERO {
                                self.long_timer.start(ctx, self.long_press.into());
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
        let style = self.button_style();
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
    Icon(Icon),
    IconAndText(IconText),
}

#[derive(PartialEq, Eq, Clone, Copy)]
pub struct ButtonStyleSheet {
    pub normal: &'static ButtonStyle,
    pub active: &'static ButtonStyle,
    pub disabled: &'static ButtonStyle,
}

#[derive(PartialEq, Eq)]
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

    fn text_style(&self, style: &ButtonStyle) -> TextStyle {
        TextStyle::new(
            style.font,
            style.text_color,
            style.button_color,
            style.text_color,
            style.text_color,
        )
    }

    /// Compute the height required to render the given text at the given width.
    /// Must be functional before placing the button.
    fn text_height(&self, text: &str, width: i16, textstyle: TextStyle) -> i16 {
        // Create rect with precise width and a large enough height to fit the text.
        let bounds = Rect::from_size(Offset::new(width, 200));
        let layout_fit = TextLayout::new(textstyle)
            .with_bounds(bounds)
            .fit_text(text);

        if let LayoutFit::OutOfBounds { .. } = layout_fit {
            debug_assert!(
                false,
                "TextLayout::fit_text returned OutOfBounds, this should not happen"
            );
        }

        layout_fit.height()
    }

    pub fn render<'s>(
        &self,
        target: &mut impl Renderer<'s>,
        area: Rect,
        style: &ButtonStyle,
        alpha: u8,
    ) {
        let text_width = area.width() - Self::ICON_SPACE;
        self.text.map(|t| {
            let text_height = self.text_height(t, text_width, self.text_style(style));
            let vertical_padding = ((area.height() - text_height) / 2).max(0);

            TextLayout::new(self.text_style(style))
                .with_top_padding(vertical_padding)
                .with_bottom_padding(vertical_padding)
                .with_bounds(area.inset(Insets::left(area.width() - text_width)))
                .render_text_with_alpha(t, target, alpha, true);
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
