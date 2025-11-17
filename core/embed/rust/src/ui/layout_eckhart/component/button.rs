#[cfg(feature = "translations")]
use crate::translations::TR;
#[cfg(feature = "haptic")]
use crate::trezorhal::haptic::{play, HapticEffect};

use crate::{
    strutil::TString,
    time::{Duration, Instant, ShortDuration},
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Marquee, Timer},
        constant,
        display::{toif::Icon, Color, Font},
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect},
        shape::{self, Renderer},
        util::split_two_lines,
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
    #[cfg(feature = "ui_debug")]
    is_cancel: bool, // used by debuglink
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
            #[cfg(feature = "ui_debug")]
            is_cancel: false,
        }
    }

    pub fn new_menu_item(text: TString<'static>, stylesheet: ButtonStyleSheet) -> Self {
        Self::with_text(text)
            .with_text_align(Self::MENU_ITEM_ALIGNMENT)
            .with_content_offset(Self::MENU_ITEM_CONTENT_OFFSET)
            .styled(stylesheet)
            .with_radius(Self::MENU_ITEM_RADIUS)
    }

    #[cfg(feature = "micropython")]
    pub fn new_cancel_menu_item(text: TString<'static>) -> Self {
        Self::with_text(text)
            .with_text_align(Self::MENU_ITEM_ALIGNMENT)
            .with_content_offset(Self::MENU_ITEM_CONTENT_OFFSET)
            .styled(theme::firmware::menu_item_title_orange())
            .with_radius(Self::MENU_ITEM_RADIUS)
            .set_is_cancel()
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

    #[cfg(feature = "ui_debug")]
    pub fn set_is_cancel(mut self) -> Self {
        self.is_cancel = true;
        self
    }

    #[cfg(not(feature = "ui_debug"))]
    pub fn set_is_cancel(self) -> Self {
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

    fn baseline_text_height(&self) -> i16 {
        // Use static string for the content height calculation to avoid misalignment
        // among keyboard buttons.
        self.style().font.visible_text_height("1")
    }

    fn baseline_subtext_height(&self) -> i16 {
        match &self.content {
            ButtonContent::TextAndSubtext { subtext_style, .. } => {
                subtext_style.text_font.visible_text_height("1")
            }
            _ => 0,
        }
    }

    fn text_height(&self, text: &str, single_line: bool, break_words: bool, width: i16) -> i16 {
        if single_line {
            self.style().font.line_height()
        } else if break_words {
            if self.stylesheet.normal.font.text_width(text) <= width {
                return self.style().font.line_height();
            } else {
                self.style().font.line_height() * 2 - constant::LINE_SPACE
            }
        } else {
            let (t1, t2) = split_two_lines(text, self.stylesheet.normal.font, width);
            if t1.is_empty() || t2.is_empty() {
                self.style().font.line_height()
            } else {
                self.style().font.line_height() * 2 - constant::LINE_SPACE
            }
        }
    }

    pub fn content_height(&self, width: i16) -> i16 {
        let width = width - 2 * Self::MENU_ITEM_CONTENT_OFFSET.x;
        match &self.content {
            ButtonContent::Empty => 0,
            ButtonContent::Text { text, single_line } => {
                text.map(|t| self.text_height(t, *single_line, false, width))
            }
            ButtonContent::Icon(icon) => icon.toif.height(),
            ButtonContent::TextAndSubtext {
                text,
                single_line,
                break_words,
                ..
            } => text.map(|t| {
                self.text_height(t, *single_line, *break_words, width)
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

    pub fn style(&self) -> &ButtonStyle {
        match self.state {
            State::Initial | State::Released => self.stylesheet.normal,
            State::Pressed => self.stylesheet.active,
            State::Disabled => self.stylesheet.disabled,
        }
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

    fn render_content<'s>(
        &'s self,
        target: &mut impl Renderer<'s>,
        stylesheet: &ButtonStyle,
        alpha: u8,
    ) {
        let mut show_text = |text: &str, render_origin: Point| {
            shape::Text::new(render_origin, text, stylesheet.font)
                .with_fg(stylesheet.text_color)
                .with_align(self.text_align)
                .with_alpha(alpha)
                .render(target)
        };
        let render_origin = |offset: Offset| {
            match self.text_align {
                Alignment::Start => self.area.left_center().ofs(self.content_offset),
                Alignment::Center => self.area.center().ofs(self.content_offset),
                Alignment::End => self.area.right_center().ofs(self.content_offset.neg()),
            }
            .ofs(offset)
        };

        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text { text, single_line } => {
                let text_baseline_height = self.baseline_text_height();
                text.map(|t| {
                    if *single_line {
                        show_text(t, render_origin(Offset::y(text_baseline_height / 2)));
                    } else {
                        let (t1, t2) = split_two_lines(
                            t,
                            stylesheet.font,
                            self.area.width() - 2 * self.content_offset.x.abs(),
                        );

                        if t1.is_empty() || t2.is_empty() {
                            show_text(t, render_origin(Offset::y(text_baseline_height / 2)));
                        } else {
                            show_text(
                                t1,
                                render_origin(Offset::y(
                                    -(text_baseline_height / 2 + constant::LINE_SPACE),
                                )),
                            );
                            show_text(
                                t2,
                                render_origin(Offset::y(
                                    text_baseline_height + constant::LINE_SPACE * 2,
                                )),
                            );
                        }
                    }
                });
            }
            ButtonContent::TextAndSubtext {
                text,
                single_line,
                break_words,
                ..
            } => {
                let text_baseline_height = self.baseline_text_height();
                let available_width = self.area.width() - 2 * self.content_offset.x;
                text.map(|t| {
                    if *single_line {
                        show_text(
                            t,
                            render_origin(Offset::y(
                                text_baseline_height / 2 - constant::LINE_SPACE * 2,
                            )),
                        );
                    } else if *break_words {
                        let first = stylesheet
                            .font
                            .longest_prefix_break_words(available_width, t);

                        if first == t {
                            // The first line fits
                            show_text(
                                first,
                                render_origin(Offset::y(
                                    text_baseline_height / 2 - constant::LINE_SPACE * 2,
                                )),
                            );
                        } else {
                            show_text(
                                first,
                                render_origin(Offset::y(
                                    -(text_baseline_height / 2 + constant::LINE_SPACE * 3),
                                )),
                            );
                            let remaining = t[first.len()..].trim();
                            if stylesheet.font.text_width(remaining) <= available_width {
                                // The second line fits
                                show_text(
                                    remaining,
                                    render_origin(Offset::y(
                                        text_baseline_height - constant::LINE_SPACE * 2,
                                    )),
                                );
                            } else {
                                // Break the second line and add the ellipsis
                                let ellipsis = "...";
                                let width = available_width - stylesheet.font.text_width(ellipsis);
                                let second =
                                    stylesheet.font.longest_prefix_break_words(width, remaining);
                                show_text(
                                    second,
                                    render_origin(Offset::y(
                                        text_baseline_height - constant::LINE_SPACE * 2,
                                    )),
                                );
                                show_text(
                                    ellipsis,
                                    render_origin(Offset::new(
                                        stylesheet.font.text_width(second),
                                        text_baseline_height - constant::LINE_SPACE * 2,
                                    )),
                                );
                            }
                        }
                    } else {
                        let (t1, t2) = split_two_lines(t, stylesheet.font, available_width);
                        if t1.is_empty() || t2.is_empty() {
                            show_text(
                                t,
                                render_origin(Offset::y(
                                    text_baseline_height / 2 - constant::LINE_SPACE * 2,
                                )),
                            );
                        } else {
                            show_text(
                                t1,
                                render_origin(Offset::y(
                                    -(text_baseline_height / 2 + constant::LINE_SPACE * 3),
                                )),
                            );
                            show_text(
                                t2,
                                render_origin(Offset::y(
                                    text_baseline_height - constant::LINE_SPACE * 2,
                                )),
                            );
                        }
                    }
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
        let style = self.style();
        self.render_background(target, style, alpha);
        self.render_content(target, style, alpha);
    }
}

impl Component for Button {
    type Msg = ButtonMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;

        if let ButtonContent::TextAndSubtext { .. } = self.content {
            let subtext_start = (bounds.height() + self.content_height(bounds.width())) / 2
                - self.baseline_subtext_height();
            if let Some(m) = self.subtext_marquee.as_mut() {
                let marquee_area = self
                    .area
                    .inset(Insets::top(subtext_start))
                    .inset(Insets::sides(self.content_offset.x));
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
        let style = self.style();
        self.render_background(target, style, 0xFF);
        self.render_content(target, style, 0xFF);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Button {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Button");
        t.bool("is_cancel", self.is_cancel);
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
