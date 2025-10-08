#[cfg(feature = "translations")]
use crate::translations::TR;
#[cfg(feature = "haptic")]
use crate::trezorhal::haptic::{play, HapticEffect};

use crate::{
    strutil::TString,
    time::{Duration, Instant, ShortDuration},
    ui::{
        component::{
            text::{layout::LayoutFit, TextStyle},
            Component, Event, EventCtx, LineBreaking, Marquee, TextLayout, Timer,
        },
        constant::{self, SCREEN},
        display::{toif::Icon, Color, Font},
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
        shape::{self, Renderer},
    },
};

use super::super::theme::{self, Gradient};

pub enum ButtonMsg {
    Pressed,
    Released,
    Clicked,
    LongPressed,
}

enum RadiusOrGradient {
    Radius(u8),
    Gradient(Gradient),
    None,
}

pub struct Button {
    area: Rect,
    touch_expand: Insets,
    content: ButtonContent,
    content_offset: Offset,
    stylesheet: ButtonStyleSheet,
    text_align: Alignment,
    radius_or_gradient: RadiusOrGradient,
    state: State,
    long_press: ShortDuration, // long press requires non-zero duration
    long_press_danger: bool,
    long_timer: Timer,
    haptic: bool,

    subtext_marquee: Option<Marquee>,
}

impl Button {
    const MENU_ITEM_RADIUS: u8 = 12;
    const MENU_ITEM_ALIGNMENT: Alignment = Alignment::Start;
    pub const MENU_ITEM_CONTENT_OFFSET: Offset = Offset::x(12);
    const CONN_ICON_WIDTH: i16 = 34;

    #[cfg(feature = "micropython")]
    const DEFAULT_STYLESHEET: ButtonStyleSheet = theme::firmware::button_default();
    #[cfg(not(feature = "micropython"))]
    const DEFAULT_STYLESHEET: ButtonStyleSheet = theme::bootloader::button_default();

    pub const fn new(content: ButtonContent) -> Self {
        let subtext_marquee = match content {
            ButtonContent::TextAndSubtext {
                subtext,
                subtext_style,
                ..
            } => Some(Marquee::new(
                subtext,
                subtext_style.text_font,
                subtext_style.text_color,
                subtext_style.background_color,
            )),
            _ => None,
        };
        Self {
            content,
            content_offset: Offset::zero(),
            area: Rect::zero(),
            touch_expand: Insets::zero(),
            stylesheet: Self::DEFAULT_STYLESHEET,
            text_align: Alignment::Center,
            radius_or_gradient: RadiusOrGradient::None,
            state: State::Initial,
            long_press: ShortDuration::ZERO,
            long_press_danger: false,
            long_timer: Timer::new(),
            haptic: true,
            subtext_marquee,
        }
    }

    pub fn new_menu_item(text: TString<'static>, stylesheet: ButtonStyleSheet) -> Self {
        Self::with_text(text)
            .with_text_align(Self::MENU_ITEM_ALIGNMENT)
            .with_content_offset(Self::MENU_ITEM_CONTENT_OFFSET)
            .styled(stylesheet)
            .with_radius(Self::MENU_ITEM_RADIUS)
    }

    pub fn new_single_line_menu_item(text: TString<'static>, stylesheet: ButtonStyleSheet) -> Self {
        Self::with_single_line_text(text)
            .with_text_align(Self::MENU_ITEM_ALIGNMENT)
            .with_content_offset(Self::MENU_ITEM_CONTENT_OFFSET)
            .styled(stylesheet)
            .with_radius(Self::MENU_ITEM_RADIUS)
    }

    pub fn new_menu_item_with_subtext(
        text: TString<'static>,
        stylesheet: ButtonStyleSheet,
        subtext: TString<'static>,
        subtext_style: &'static TextStyle,
    ) -> Self {
        Self::with_text_and_subtext(text, subtext, subtext_style)
            .with_text_align(Self::MENU_ITEM_ALIGNMENT)
            .with_content_offset(Self::MENU_ITEM_CONTENT_OFFSET)
            .styled(stylesheet)
            .with_radius(Self::MENU_ITEM_RADIUS)
    }

    pub fn new_single_line_menu_item_with_subtext(
        text: TString<'static>,
        stylesheet: ButtonStyleSheet,
        subtext: TString<'static>,
        subtext_style: &'static TextStyle,
    ) -> Self {
        Self::with_single_line_text_and_subtext(text, subtext, subtext_style)
            .with_text_align(Self::MENU_ITEM_ALIGNMENT)
            .with_content_offset(Self::MENU_ITEM_CONTENT_OFFSET)
            .styled(stylesheet)
            .with_radius(Self::MENU_ITEM_RADIUS)
    }

    #[cfg(feature = "micropython")]
    pub fn new_connection_item(
        text: TString<'static>,
        stylesheet: ButtonStyleSheet,
        connected: bool,
    ) -> Self {
        let (subtext, subtext_style) = if connected {
            (
                TR::words__connected.into(),
                &theme::TEXT_MENU_ITEM_SUBTITLE_GREEN,
            )
        } else {
            (
                TR::words__disconnected.into(),
                &theme::TEXT_MENU_ITEM_SUBTITLE,
            )
        };

        Self::with_clipped_text_and_subtext(text, subtext, subtext_style)
            .with_text_align(Self::MENU_ITEM_ALIGNMENT)
            .with_content_offset(Self::MENU_ITEM_CONTENT_OFFSET)
            .styled(stylesheet)
            .with_radius(Self::MENU_ITEM_RADIUS)
    }

    pub const fn with_single_line_text(text: TString<'static>) -> Self {
        Self::new(ButtonContent::single_line_text(text))
    }

    pub const fn with_text(text: TString<'static>) -> Self {
        Self::new(ButtonContent::text(text))
    }

    pub fn with_text_and_subtext(
        text: TString<'static>,
        subtext: TString<'static>,
        subtext_style: &'static TextStyle,
    ) -> Self {
        Self::new(ButtonContent::text_and_subtext(
            text,
            subtext,
            subtext_style,
        ))
    }

    pub fn with_clipped_text_and_subtext(
        text: TString<'static>,
        subtext: TString<'static>,
        subtext_style: &'static TextStyle,
    ) -> Self {
        Self::new(ButtonContent::clipped_text_and_subtext(
            text,
            subtext,
            subtext_style,
        ))
    }

    pub fn with_single_line_text_and_subtext(
        text: TString<'static>,
        subtext: TString<'static>,
        subtext_style: &'static TextStyle,
    ) -> Self {
        Self::new(ButtonContent::single_line_text_and_subtext(
            text,
            subtext,
            subtext_style,
        ))
    }

    pub const fn with_icon(icon: Icon) -> Self {
        Self::new(ButtonContent::Icon(icon))
    }

    #[cfg(feature = "micropython")]
    pub const fn with_homebar_content(text: Option<TString<'static>>) -> Self {
        Self::new(ButtonContent::HomeBar(text))
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

    pub const fn with_content_offset(mut self, offset: Offset) -> Self {
        self.content_offset = offset;
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

    pub fn with_long_press_danger(mut self, danger: bool) -> Self {
        self.long_press_danger = danger;
        self
    }

    pub fn with_radius(mut self, radius: u8) -> Self {
        self.radius_or_gradient = RadiusOrGradient::Radius(radius);
        self
    }

    pub fn without_haptics(mut self) -> Self {
        self.haptic = false;
        self
    }

    pub fn with_gradient(mut self, gradient: Gradient) -> Self {
        self.radius_or_gradient = RadiusOrGradient::Gradient(gradient);
        self
    }

    pub fn has_gradient(&self) -> bool {
        matches!(self.radius_or_gradient, RadiusOrGradient::Gradient(_))
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
        if let Some(m) = &mut self.subtext_marquee {
            m.start(ctx, Instant::now());
        }
        self.set(ctx, State::Initial)
    }

    pub fn disable(&mut self, ctx: &mut EventCtx) {
        if let Some(m) = &mut self.subtext_marquee {
            m.reset();
        }
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

    pub fn long_press(&self) -> Option<(Duration, bool)> {
        if self.long_press != ShortDuration::ZERO {
            Some((self.long_press.into(), self.long_press_danger))
        } else {
            None
        }
    }

    pub fn is_disabled(&self) -> bool {
        matches!(self.state, State::Disabled)
    }

    pub fn set_content(&mut self, content: ButtonContent) {
        self.content = content
    }

    pub fn set_expanded_touch_area(&mut self, expand: Insets) {
        self.touch_expand = expand;
    }

    pub fn set_content_offset(&mut self, offset: Offset) {
        self.content_offset = offset;
    }

    pub const fn content(&self) -> &ButtonContent {
        &self.content
    }

    pub fn content_mut(&mut self) -> &mut ButtonContent {
        &mut self.content
    }

    pub fn content_offset(&self) -> Offset {
        self.content_offset
    }

    fn baseline_subtext_height(&self) -> i16 {
        match &self.content {
            ButtonContent::TextAndSubtext { subtext_style, .. } => {
                subtext_style.text_font.text_height()
            }
            _ => 0,
        }
    }

    /// Compute the height required to render the given text at the given width.
    /// Must be functional before placing the button.
    fn text_height(&self, text: &str, width: i16, single_line: bool, break_words: bool) -> i16 {
        let textstyle = self.text_style();

        // Adjust text style line breaking
        let textstyle = if break_words {
            textstyle.with_line_breaking(LineBreaking::BreakWordsNoHyphen)
        } else {
            textstyle.with_line_breaking(LineBreaking::BreakAtWhitespace)
        };

        // Limit the maximum height
        let max_height = if single_line {
            textstyle.text_font.text_max_height()
        } else {
            2 * textstyle.text_font.text_max_height()
        };

        // Create rect with precise width and a large enough height to fit the text.
        let bounds = Rect::from_size(Offset::new(width, SCREEN.height()));
        let layout_fit = TextLayout::new(textstyle)
            .with_bounds(bounds)
            .fit_text(text);

        if let LayoutFit::OutOfBounds { .. } = layout_fit {
            debug_assert!(
                false,
                "TextLayout::fit_text returned OutOfBounds, this should not happen"
            );
        }

        layout_fit.height().min(max_height)
    }

    /// Returns the height required to render the button content at the given full
    /// button width (including the padding). Must be functional before placing the
    /// button.
    pub fn content_height(&self, button_width: i16) -> i16 {
        let width = match self.text_align {
            Alignment::Center => button_width - self.content_offset.x.abs(),
            _ => button_width - 2 * self.content_offset.x.max(0),
        };

        match &self.content {
            ButtonContent::Empty => 0,
            ButtonContent::Text { text, single_line } => {
                text.map(|t| self.text_height(t, width, *single_line, false))
            }
            ButtonContent::Icon(icon) => icon.toif.height(),
            ButtonContent::TextAndSubtext {
                text,
                single_line,
                break_words,
                ..
            } => text.map(|t| {
                self.text_height(t, width, *single_line, *break_words)
                    + constant::LINE_SPACE
                    + self.baseline_subtext_height()
            }),
            #[cfg(feature = "micropython")]
            ButtonContent::HomeBar(..) => theme::ACTION_BAR_HEIGHT,
        }
    }

    pub fn set_stylesheet(&mut self, stylesheet: ButtonStyleSheet) {
        if self.stylesheet != stylesheet {
            self.stylesheet = stylesheet;
        }
    }

    pub fn button_style(&self) -> &ButtonStyle {
        match self.state {
            State::Initial | State::Released => self.stylesheet.normal,
            State::Pressed => self.stylesheet.active,
            State::Disabled => self.stylesheet.disabled,
        }
    }

    fn text_style(&self) -> TextStyle {
        let stylesheet = self.button_style();
        TextStyle::new(
            stylesheet.font,
            stylesheet.text_color,
            stylesheet.button_color,
            stylesheet.text_color,
            stylesheet.text_color,
        )
    }

    pub fn stylesheet(&self) -> &ButtonStyleSheet {
        &self.stylesheet
    }

    pub fn area(&self) -> Rect {
        self.area
    }

    pub fn touch_area(&self) -> Rect {
        self.area.outset(self.touch_expand)
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
        match self.radius_or_gradient {
            RadiusOrGradient::Radius(radius) => {
                shape::Bar::new(self.area)
                    .with_bg(style.button_color)
                    .with_fg(style.button_color)
                    .with_radius(radius as i16)
                    .with_thickness(2)
                    .with_alpha(alpha)
                    .render(target);
            }
            // Gradient bar is rendered only in `normal` state, not `active` or `disabled`
            RadiusOrGradient::Gradient(gradient) if self.state.is_normal() => {
                gradient.render(target, self.area, 1);
            }
            _ => {
                shape::Bar::new(self.area)
                    .with_bg(style.button_color)
                    .with_fg(style.button_color)
                    .with_alpha(alpha)
                    .render(target);
            }
        }
    }

    /// Returns the vertical padding required to center the button content.
    /// Functional only after placing the button.
    fn vertical_padding(&self) -> i16 {
        ((self.area.height() - self.content_height(self.area.width())) / 2).max(0)
    }

    fn render_text<'s>(
        &'s self,
        text: &str,
        target: &mut impl Renderer<'s>,
        alpha: u8,
        must_fit: bool,
    ) {
        let vertical_padding = self.vertical_padding();

        let side_insets = match (self.text_align, self.content_offset.x) {
            (Alignment::Center, x) if x >= 0 => Insets::new(0, 0, 0, x),
            (Alignment::Center, x) => Insets::new(0, x.abs(), 0, 0),
            (_, x) => Insets::new(0, x.max(0), 0, x.max(0)),
        };
        dbg_println!(
            "is center align {:?}, content offset x {:?}, left inset {:?}, right inset {:?}",
            self.text_align == Alignment::Center,
            self.content_offset.x,
            side_insets.left,
            side_insets.right
        );
        let bounds = self.area().inset(side_insets);

        TextLayout::new(self.text_style())
            .with_bounds(bounds)
            .with_top_padding(vertical_padding)
            .with_bottom_padding(vertical_padding)
            .with_align(self.text_align)
            .render_text_with_alpha(text, target, alpha, must_fit);
    }

    fn render_content<'s>(
        &'s self,
        target: &mut impl Renderer<'s>,
        stylesheet: &ButtonStyle,
        alpha: u8,
    ) {
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text { text, single_line } => {
                text.map(|t| {
                    self.render_text(t, target, alpha, *single_line);
                });
            }
            ButtonContent::TextAndSubtext {
                text,
                single_line,
                break_words,
                ..
            } => {
                text.map(|t| {
                    self.render_text(t, target, alpha, *single_line || !*break_words);
                });

                if let Some(m) = &self.subtext_marquee {
                    m.render(target);
                } else {
                    unreachable!();
                };
            }
            ButtonContent::Icon(icon) => {
                shape::ToifImage::new(self.area.center() + self.content_offset, icon.toif)
                    .with_align(Alignment2D::CENTER)
                    .with_fg(stylesheet.icon_color)
                    .with_alpha(alpha)
                    .render(target);
            }
            #[cfg(feature = "micropython")]
            ButtonContent::HomeBar(text) => {
                let baseline = self.area.center();
                if let Some(text) = text {
                    const OFFSET_Y: Offset = Offset::y(16);
                    text.map(|text| {
                        shape::Text::new(baseline, text, stylesheet.font)
                            .with_fg(stylesheet.text_color)
                            .with_align(Alignment::Center)
                            .with_alpha(alpha)
                            .render(target);
                    });
                    shape::ToifImage::new(self.area.center() + OFFSET_Y, theme::ICON_MINUS.toif)
                        .with_fg(stylesheet.icon_color)
                        .with_align(Alignment2D::CENTER)
                        .render(target);
                } else {
                    // Menu icon in the middle
                    shape::ToifImage::new(baseline, theme::ICON_MENU.toif)
                        .with_fg(stylesheet.icon_color)
                        .with_align(Alignment2D::CENTER)
                        .render(target);
                }
            }
        }
    }

    pub fn render_with_alpha<'s>(&'s self, target: &mut impl Renderer<'s>, alpha: u8) {
        let style = self.button_style();
        self.render_background(target, style, alpha);
        self.render_content(target, style, alpha);
    }
}

impl Component for Button {
    type Msg = ButtonMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;

        if let ButtonContent::TextAndSubtext { .. } = self.content {
            let content_height = self.content_height(bounds.width());
            let vertical_padding = (bounds.height() - content_height) / 2;
            let subtext_height = self.baseline_subtext_height();
            if let Some(m) = self.subtext_marquee.as_mut() {
                let marquee_area = self.area.inset(Insets::new(
                    vertical_padding + content_height - subtext_height,
                    self.content_offset.x,
                    vertical_padding,
                    self.content_offset.x,
                ));
                m.place(marquee_area);
            }
        }

        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(m) = &mut self.subtext_marquee {
            m.event(ctx, event);
        }
        let touch_area = self.touch_area();
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
                            if let Some((duration, _danger)) = self.long_press() {
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
            ButtonContent::Text { text, .. } => t.string("text", *text),
            ButtonContent::Icon(_) => t.bool("icon", true),
            ButtonContent::TextAndSubtext { text, .. } => {
                t.string("text", *text);
            }
            #[cfg(feature = "micropython")]
            ButtonContent::HomeBar(text) => {
                t.string("text", text.unwrap_or(TString::empty()));
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

impl State {
    /// Returns true if the button is in a normal state (not pressed or
    /// disabled).
    fn is_normal(&self) -> bool {
        matches!(self, State::Initial | State::Released)
    }
}

#[derive(Clone)]
pub enum ButtonContent {
    Empty,
    Text {
        text: TString<'static>,
        single_line: bool,
    },
    TextAndSubtext {
        text: TString<'static>,
        single_line: bool,
        break_words: bool,
        subtext: TString<'static>,
        subtext_style: &'static TextStyle,
    },
    Icon(Icon),
    #[cfg(feature = "micropython")]
    HomeBar(Option<TString<'static>>),
}

impl ButtonContent {
    pub const fn text(text: TString<'static>) -> Self {
        Self::Text {
            text,
            single_line: false,
        }
    }

    pub const fn single_line_text(text: TString<'static>) -> Self {
        Self::Text {
            text,
            single_line: true,
        }
    }

    pub const fn text_and_subtext(
        text: TString<'static>,
        subtext: TString<'static>,
        subtext_style: &'static TextStyle,
    ) -> Self {
        Self::TextAndSubtext {
            text,
            single_line: false,
            break_words: false,
            subtext,
            subtext_style,
        }
    }

    pub const fn clipped_text_and_subtext(
        text: TString<'static>,
        subtext: TString<'static>,
        subtext_style: &'static TextStyle,
    ) -> Self {
        Self::TextAndSubtext {
            text,
            single_line: false,
            break_words: true,
            subtext,
            subtext_style,
        }
    }

    pub const fn single_line_text_and_subtext(
        text: TString<'static>,
        subtext: TString<'static>,
        subtext_style: &'static TextStyle,
    ) -> Self {
        Self::TextAndSubtext {
            text,
            single_line: true,
            break_words: false,
            subtext,
            subtext_style,
        }
    }
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
}
