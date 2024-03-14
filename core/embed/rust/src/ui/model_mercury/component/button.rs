#[cfg(feature = "haptic")]
use crate::trezorhal::haptic::{play, HapticEffect};
use crate::{
    time::Duration,
    ui::{
        component::{
            Component, ComponentExt, Event, EventCtx, FixedHeightBar, MsgMap, Split, TimerToken,
        },
        display::{self, toif::Icon, Color, Font},
        event::TouchEvent,
        geometry::{Alignment2D, Insets, Offset, Point, Rect},
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

pub struct Button<T> {
    area: Rect,
    touch_expand: Option<Insets>,
    content: ButtonContent<T>,
    styles: ButtonStyleSheet,
    state: State,
    long_press: Option<Duration>,
    long_timer: Option<TimerToken>,
}

impl<T> Button<T> {
    /// Offsets the baseline of the button text
    /// -x/+x => left/right
    /// -y/+y => up/down
    pub const BASELINE_OFFSET: Offset = Offset::new(2, 6);

    pub const fn new(content: ButtonContent<T>) -> Self {
        Self {
            content,
            area: Rect::zero(),
            touch_expand: None,
            styles: theme::button_default(),
            state: State::Initial,
            long_press: None,
            long_timer: None,
        }
    }

    pub const fn with_text(text: T) -> Self {
        Self::new(ButtonContent::Text(text))
    }

    pub const fn with_icon(icon: Icon) -> Self {
        Self::new(ButtonContent::Icon(icon))
    }

    pub const fn with_icon_and_text(content: IconText<T>) -> Self {
        Self::new(ButtonContent::IconAndText::<T>(content))
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

    pub const fn with_expanded_touch_area(mut self, expand: Insets) -> Self {
        self.touch_expand = Some(expand);
        self
    }

    pub fn with_long_press(mut self, duration: Duration) -> Self {
        self.long_press = Some(duration);
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

    pub fn set_content(&mut self, ctx: &mut EventCtx, content: ButtonContent<T>)
    where
        T: PartialEq,
    {
        if self.content != content {
            self.content = content;
            ctx.request_paint();
        }
    }

    pub fn content(&self) -> &ButtonContent<T> {
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
                if style.border_width > 0 {
                    // Paint the border and a smaller background on top of it.
                    display::rect_fill_rounded(
                        self.area,
                        style.border_color,
                        style.background_color,
                        style.border_radius,
                    );
                    display::rect_fill_rounded(
                        self.area.inset(Insets::uniform(style.border_width)),
                        style.button_color,
                        style.border_color,
                        style.border_radius,
                    );
                } else {
                    // We do not need to draw an explicit border in this case, just a
                    // bigger background.
                    display::rect_fill_rounded(
                        self.area,
                        style.button_color,
                        style.background_color,
                        style.border_radius,
                    );
                }
            }
        }
    }

    pub fn render_background<'s>(&self, target: &mut impl Renderer<'s>, style: &ButtonStyle) {
        match &self.content {
            ButtonContent::IconBlend(_, _, _) => {}
            _ => shape::Bar::new(self.area)
                .with_bg(style.button_color)
                .with_fg(style.border_color)
                .with_thickness(style.border_width)
                .with_radius(style.border_radius as i16)
                .render(target),
        }
    }

    pub fn paint_content(&self, style: &ButtonStyle)
    where
        T: AsRef<str>,
    {
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text(text) => {
                let text = text.as_ref();
                let start_of_baseline = self.area.center() + Self::BASELINE_OFFSET;
                display::text_left(
                    start_of_baseline,
                    text,
                    style.font,
                    style.text_color,
                    style.button_color,
                );
            }
            ButtonContent::Icon(icon) => {
                icon.draw(
                    self.area.center(),
                    Alignment2D::CENTER,
                    style.text_color,
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

    pub fn render_content<'s>(&self, target: &mut impl Renderer<'s>, style: &ButtonStyle)
    where
        T: AsRef<str>,
    {
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text(text) => {
                let text = text.as_ref();
                let start_of_baseline = self.area.left_center() + Self::BASELINE_OFFSET;
                shape::Text::new(start_of_baseline, text)
                    .with_font(style.font)
                    .with_fg(style.text_color)
                    .render(target);
            }
            ButtonContent::Icon(icon) => {
                shape::ToifImage::new(self.area.center(), icon.toif)
                    .with_align(Alignment2D::CENTER)
                    .with_fg(style.text_color)
                    .render(target);
            }
            ButtonContent::IconAndText(child) => {
                child.render(target, self.area, style, Self::BASELINE_OFFSET);
            }
            ButtonContent::IconBlend(bg, fg, offset) => {
                shape::Bar::new(self.area)
                    .with_bg(style.background_color)
                    .render(target);
                shape::ToifImage::new(self.area.top_left(), bg.toif)
                    .with_fg(style.button_color)
                    .render(target);
                shape::ToifImage::new(self.area.top_left() + *offset, fg.toif)
                    .with_fg(style.text_color)
                    .render(target);
            }
        }
    }
}

impl<T> Component for Button<T>
where
    T: AsRef<str>,
{
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
                            play(HapticEffect::ButtonPress);
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
                        play(HapticEffect::ButtonPress);
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
        self.render_background(target, style);
        self.render_content(target, style);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Button<T>
where
    T: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Button");
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text(text) => t.string("text", text.as_ref().into()),
            ButtonContent::Icon(_) => t.bool("icon", true),
            ButtonContent::IconAndText(content) => {
                t.string("text", content.text.as_ref().into());
                t.bool("icon", true);
            }
            ButtonContent::IconBlend(_, _, _) => t.bool("icon", true),
        }
    }
}

#[derive(PartialEq, Eq)]
enum State {
    Initial,
    Pressed,
    Released,
    Disabled,
}

#[derive(PartialEq, Eq)]
pub enum ButtonContent<T> {
    Empty,
    Text(T),
    Icon(Icon),
    IconAndText(IconText<T>),
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
    pub background_color: Color,
    pub border_color: Color,
    pub border_radius: u8,
    pub border_width: i16,
}

impl<T> Button<T> {
    pub fn cancel_confirm(
        left: Button<T>,
        right: Button<T>,
        left_is_small: bool,
    ) -> CancelConfirm<
        T,
        impl Fn(ButtonMsg) -> Option<CancelConfirmMsg>,
        impl Fn(ButtonMsg) -> Option<CancelConfirmMsg>,
    >
    where
        T: AsRef<str>,
    {
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
        left: Option<T>,
        right: Option<T>,
    ) -> CancelConfirm<
        T,
        impl Fn(ButtonMsg) -> Option<CancelConfirmMsg>,
        impl Fn(ButtonMsg) -> Option<CancelConfirmMsg>,
    >
    where
        T: AsRef<str>,
    {
        let left_is_small: bool;

        let left = if let Some(verb) = left {
            left_is_small = verb.as_ref().len() <= 4;
            if verb.as_ref() == "^" {
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
        confirm: T,
        info: T,
    ) -> CancelInfoConfirm<
        T,
        impl Fn(ButtonMsg) -> Option<CancelInfoConfirmMsg>,
        impl Fn(ButtonMsg) -> Option<CancelInfoConfirmMsg>,
        impl Fn(ButtonMsg) -> Option<CancelInfoConfirmMsg>,
    >
    where
        T: AsRef<str>,
    {
        let right = Button::with_text(confirm)
            .styled(theme::button_confirm())
            .map(|msg| {
                (matches!(msg, ButtonMsg::Clicked)).then(|| CancelInfoConfirmMsg::Confirmed)
            });
        let top = Button::with_text(info)
            .styled(theme::button_moreinfo())
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

pub enum CancelConfirmMsg {
    Cancelled,
    Confirmed,
}

type CancelInfoConfirm<T, F0, F1, F2> = FixedHeightBar<
    Split<MsgMap<Button<T>, F0>, Split<MsgMap<Button<T>, F1>, MsgMap<Button<T>, F2>>>,
>;

type CancelConfirm<T, F0, F1> = FixedHeightBar<Split<MsgMap<Button<T>, F0>, MsgMap<Button<T>, F1>>>;

#[derive(Clone, Copy)]
pub enum CancelInfoConfirmMsg {
    Cancelled,
    Info,
    Confirmed,
}

pub enum SelectWordMsg {
    Selected(usize),
}

#[derive(PartialEq, Eq)]
pub struct IconText<T> {
    text: T,
    icon: Icon,
}

impl<T> IconText<T>
where
    T: AsRef<str>,
{
    const ICON_SPACE: i16 = 46;
    const ICON_MARGIN: i16 = 4;
    const TEXT_MARGIN: i16 = 6;

    pub fn new(text: T, icon: Icon) -> Self {
        Self { text, icon }
    }

    pub fn paint(&self, area: Rect, style: &ButtonStyle, baseline_offset: Offset) {
        let width = style.font.text_width(self.text.as_ref());

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
            display::text_left(
                text_pos,
                self.text.as_ref(),
                style.font,
                style.text_color,
                style.button_color,
            );
        }

        if use_icon {
            self.icon.draw(
                icon_pos,
                Alignment2D::CENTER,
                style.text_color,
                style.button_color,
            );
        }
    }
    pub fn render<'s>(
        & self,
        target: &mut impl Renderer<'s>,
        area: Rect,
        style: &ButtonStyle,
        baseline_offset: Offset,
    ) {
        let width = style.font.text_width(self.text.as_ref());

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
            shape::Text::new(text_pos, self.text.as_ref())
                .with_fg(style.text_color)
                .render(target);
        }
        if use_icon {
            shape::ToifImage::new(icon_pos, self.icon.toif)
                .with_align(Alignment2D::CENTER)
                .with_fg(style.text_color)
                .render(target);
        }
    }
}
