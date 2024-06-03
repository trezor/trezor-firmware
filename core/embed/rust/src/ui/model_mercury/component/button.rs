#[cfg(feature = "haptic")]
use crate::trezorhal::haptic::{play, HapticEffect};
use crate::{
    strutil::TString,
    time::Duration,
    ui::{
        component::{
            Component, ComponentExt, Event, EventCtx, FixedHeightBar, MsgMap, Split, TimerToken,
        },
        display::{self, toif::Icon, Color, Font},
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect},
        shape,
        shape::Renderer,
    },
};

use super::theme;

pub enum ButtonMsg {
    Pressed,
    Released,
    Clicked,
    LongPressed,
}

#[derive(Clone)]
pub struct Button {
    area: Rect,
    touch_expand: Option<Insets>,
    content: ButtonContent,
    styles: ButtonStyleSheet,
    text_align: Alignment,
    radius: Option<u8>,
    state: State,
    long_press: Option<Duration>,
    long_timer: Option<TimerToken>,
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
            touch_expand: None,
            styles: theme::button_default(),
            text_align: Alignment::Start,
            radius: None,
            state: State::Initial,
            long_press: None,
            long_timer: None,
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

    pub const fn with_icon_blend(bg: Icon, fg: Icon, fg_offset: Offset) -> Self {
        Self::new(ButtonContent::IconBlend(bg, fg, fg_offset))
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

    pub fn is_disabled(&self) -> bool {
        matches!(self.state, State::Disabled)
    }

    pub fn set_content(&mut self, ctx: &mut EventCtx, content: ButtonContent) {
        if self.content != content {
            self.content = content;
            ctx.request_paint();
        }
    }

    pub fn content(&self) -> &ButtonContent {
        &self.content
    }

    pub fn set_stylesheet(&mut self, ctx: &mut EventCtx, styles: ButtonStyleSheet) {
        if self.styles != styles {
            self.styles = styles;
            ctx.request_paint();
        }
    }

    pub fn style(&self) -> &ButtonStyle {
        match self.state {
            State::Initial | State::Released => self.styles.normal,
            State::Pressed => self.styles.active,
            State::Disabled => self.styles.disabled,
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

    pub fn paint_background(&self, style: &ButtonStyle) {
        match &self.content {
            ButtonContent::IconBlend(_, _, _) => {}
            _ => {
                display::rect_fill(self.area, style.button_color);
            }
        }
    }

    pub fn render_background<'s>(
        &self,
        target: &mut impl Renderer<'s>,
        style: &ButtonStyle,
        alpha: u8,
    ) {
        match &self.content {
            ButtonContent::IconBlend(_, _, _) => {}
            _ => {
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
        }
    }

    pub fn paint_content(&self, style: &ButtonStyle) {
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text(text) => {
                let start_of_baseline = self.area.center() + Self::BASELINE_OFFSET;
                text.map(|text| {
                    display::text_left(
                        start_of_baseline,
                        text,
                        style.font,
                        style.text_color,
                        style.button_color,
                    );
                });
            }
            ButtonContent::Icon(icon) => {
                icon.draw(
                    self.area.center(),
                    Alignment2D::CENTER,
                    style.icon_color,
                    style.button_color,
                );
            }
            ButtonContent::IconAndText(child) => {
                child.paint(self.area, self.style(), Self::BASELINE_OFFSET);
            }
            ButtonContent::IconBlend(bg, fg, offset) => display::icon_over_icon(
                Some(self.area),
                (*bg, Offset::zero(), style.button_color),
                (*fg, *offset, style.text_color),
                style.background_color,
            ),
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
                let y_offset = Offset::y(self.style().font.allcase_text_height() / 2);
                let start_of_baseline = match self.text_align {
                    Alignment::Start => {
                        self.area.left_center() + Offset::x(Self::BASELINE_OFFSET.x)
                    }
                    Alignment::Center => self.area.center(),
                    Alignment::End => self.area.right_center() - Offset::x(Self::BASELINE_OFFSET.x),
                } + y_offset;
                text.map(|text| {
                    shape::Text::new(start_of_baseline, text)
                        .with_font(style.font)
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
                child.render(
                    target,
                    self.area,
                    self.style(),
                    Self::BASELINE_OFFSET,
                    alpha,
                );
            }
            ButtonContent::IconBlend(bg, fg, offset) => {
                shape::Bar::new(self.area)
                    .with_bg(style.background_color)
                    .with_alpha(alpha)
                    .render(target);
                shape::ToifImage::new(self.area.top_left(), bg.toif)
                    .with_fg(style.button_color)
                    .with_alpha(alpha)
                    .render(target);
                shape::ToifImage::new(self.area.top_left() + *offset, fg.toif)
                    .with_fg(style.icon_color)
                    .with_alpha(alpha)
                    .render(target);
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
                                self.long_timer = Some(ctx.request_timer(duration));
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
                    _ => {
                        // Touch finished outside our area.
                        self.set(ctx, State::Initial);
                        self.long_timer = None;
                    }
                }
            }
            Event::Timer(token) => {
                if self.long_timer == Some(token) {
                    self.long_timer = None;
                    if matches!(self.state, State::Pressed) {
                        #[cfg(feature = "haptic")]
                        if self.haptic {
                            play(HapticEffect::ButtonPress);
                        }
                        self.set(ctx, State::Initial);
                        return Some(ButtonMsg::LongPressed);
                    }
                }
            }
            _ => {}
        };
        None
    }

    fn paint(&mut self) {
        let style = self.style();
        self.paint_background(style);
        self.paint_content(style);
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let style = self.style();
        self.render_background(target, style, 0xFF);
        self.render_content(target, style, 0xFF);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
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
            ButtonContent::IconBlend(_, _, _) => t.bool("icon", true),
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
    IconBlend(Icon, Icon, Offset),
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

impl Button {
    pub fn cancel_confirm(
        left: Button,
        right: Button,
        left_is_small: bool,
    ) -> CancelConfirm<
        impl Fn(ButtonMsg) -> Option<CancelConfirmMsg>,
        impl Fn(ButtonMsg) -> Option<CancelConfirmMsg>,
    > {
        let width = if left_is_small {
            theme::BUTTON_WIDTH
        } else {
            0
        };
        theme::button_bar(Split::left(
            width,
            theme::BUTTON_SPACING,
            left.map(|msg| {
                (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Cancelled)
            }),
            right.map(|msg| {
                (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
            }),
        ))
    }

    pub fn cancel_confirm_text(
        left: Option<TString<'static>>,
        right: Option<TString<'static>>,
    ) -> CancelConfirm<
        impl Fn(ButtonMsg) -> Option<CancelConfirmMsg>,
        impl Fn(ButtonMsg) -> Option<CancelConfirmMsg>,
    > {
        let left_is_small: bool;

        let left = if let Some(verb) = left {
            left_is_small = verb.len() <= 4;
            if verb == "^".into() {
                Button::with_icon(theme::ICON_UP)
            } else {
                Button::with_text(verb)
            }
        } else {
            left_is_small = right.is_some();
            Button::with_icon(theme::ICON_CANCEL)
        };
        let right = if let Some(verb) = right {
            Button::with_text(verb).styled(theme::button_confirm())
        } else {
            Button::with_icon(theme::ICON_CONFIRM).styled(theme::button_confirm())
        };
        Self::cancel_confirm(left, right, left_is_small)
    }

    pub fn cancel_info_confirm(
        confirm: TString<'static>,
        info: TString<'static>,
    ) -> CancelInfoConfirm<
        impl Fn(ButtonMsg) -> Option<CancelInfoConfirmMsg>,
        impl Fn(ButtonMsg) -> Option<CancelInfoConfirmMsg>,
        impl Fn(ButtonMsg) -> Option<CancelInfoConfirmMsg>,
    > {
        let right = Button::with_text(confirm)
            .styled(theme::button_confirm())
            .map(|msg| {
                (matches!(msg, ButtonMsg::Clicked)).then(|| CancelInfoConfirmMsg::Confirmed)
            });
        let top = Button::with_text(info)
            .styled(theme::button_default())
            .map(|msg| (matches!(msg, ButtonMsg::Clicked)).then(|| CancelInfoConfirmMsg::Info));
        let left = Button::with_icon(theme::ICON_CANCEL).map(|msg| {
            (matches!(msg, ButtonMsg::Clicked)).then(|| CancelInfoConfirmMsg::Cancelled)
        });
        let total_height = theme::BUTTON_HEIGHT + theme::BUTTON_SPACING + theme::INFO_BUTTON_HEIGHT;
        FixedHeightBar::bottom(
            Split::top(
                theme::INFO_BUTTON_HEIGHT,
                theme::BUTTON_SPACING,
                top,
                Split::left(theme::BUTTON_WIDTH, theme::BUTTON_SPACING, left, right),
            ),
            total_height,
        )
    }
}

#[derive(Copy, Clone)]
pub enum CancelConfirmMsg {
    Cancelled,
    Confirmed,
}

type CancelInfoConfirm<F0, F1, F2> =
    FixedHeightBar<Split<MsgMap<Button, F0>, Split<MsgMap<Button, F1>, MsgMap<Button, F2>>>>;

type CancelConfirm<F0, F1> = FixedHeightBar<Split<MsgMap<Button, F0>, MsgMap<Button, F1>>>;

#[derive(Clone, Copy)]
pub enum CancelInfoConfirmMsg {
    Cancelled,
    Info,
    Confirmed,
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

    pub fn paint(&self, area: Rect, style: &ButtonStyle, baseline_offset: Offset) {
        let width = self.text.map(|t| style.font.text_width(t));
        let height = style.font.text_height();

        let mut use_icon = false;
        let mut use_text = false;

        let mut icon_pos = Point::new(
            area.top_left().x + ((Self::ICON_SPACE + Self::ICON_MARGIN) / 2),
            area.center().y,
        );
        let mut text_pos = area.center() + Offset::new(-width / 2, height / 2) + baseline_offset;

        if area.width() > (Self::ICON_SPACE + Self::TEXT_MARGIN + width) {
            //display both icon and text
            text_pos = Point::new(area.top_left().x + Self::ICON_SPACE, text_pos.y);
            use_text = true;
            use_icon = true;
        } else if area.width() > (width + Self::TEXT_MARGIN) {
            use_text = true;
        } else {
            //if we can't fit the text, retreat to centering the icon
            icon_pos = area.center();
            use_icon = true;
        }

        if use_text {
            self.text.map(|t| {
                display::text_left(
                    text_pos,
                    t,
                    style.font,
                    style.text_color,
                    style.button_color,
                )
            });
        }

        if use_icon {
            self.icon.draw(
                icon_pos,
                Alignment2D::CENTER,
                style.icon_color,
                style.button_color,
            );
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
        let width = self.text.map(|t| style.font.text_width(t));

        let mut use_icon = false;
        let mut use_text = false;

        let mut icon_pos = Point::new(
            area.top_left().x + ((Self::ICON_SPACE + Self::ICON_MARGIN) / 2),
            area.center().y,
        );
        let mut text_pos = area.left_center() + baseline_offset;

        if area.width() > (Self::ICON_SPACE + Self::TEXT_MARGIN + width) {
            //display both icon and text
            text_pos = Point::new(area.top_left().x + Self::ICON_SPACE, text_pos.y);
            use_text = true;
            use_icon = true;
        } else if area.width() > (width + Self::TEXT_MARGIN) {
            use_text = true;
        } else {
            //if we can't fit the text, retreat to centering the icon
            icon_pos = area.center();
            use_icon = true;
        }

        if use_text {
            self.text.map(|t| {
                shape::Text::new(text_pos, t)
                    .with_font(style.font)
                    .with_fg(style.text_color)
                    .with_alpha(alpha)
                    .render(target)
            });
        }

        if use_icon {
            shape::ToifImage::new(icon_pos, self.icon.toif)
                .with_align(Alignment2D::CENTER)
                .with_fg(style.icon_color)
                .with_alpha(alpha)
                .render(target);
        }
    }
}
