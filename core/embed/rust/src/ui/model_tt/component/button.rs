use crate::{
    time::Duration,
    ui::{
        component::{
            Component, ComponentExt, Event, EventCtx, FixedHeightBar, Floating, Map, Paginate,
            Split, TimerToken,
        },
        display::{self, toif::Icon, Color, Font},
        event::TouchEvent,
        geometry::{Insets, Offset, Point, Rect, CENTER},
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
    /// Offsets the baseline of the button text either up (negative) or down
    /// (positive).
    pub const BASELINE_OFFSET: i16 = -3;

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

    pub fn paint_content(&self, style: &ButtonStyle)
    where
        T: AsRef<str>,
    {
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text(text) => {
                let text = text.as_ref();
                let width = style.font.text_width(text);
                let height = style.font.text_height();
                let start_of_baseline = self.area.center()
                    + Offset::new(-width / 2, height / 2)
                    + Offset::y(Self::BASELINE_OFFSET);
                display::text(
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
                    CENTER,
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

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Button<T>
where
    T: AsRef<str> + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Button");
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text(text) => t.field("text", text),
            ButtonContent::Icon(_) => t.symbol("icon"),
            ButtonContent::IconAndText(_) => {}
            ButtonContent::IconBlend(_, _, _) => t.symbol("icon"),
        }
        t.close();
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
    IconAndText(IconText),
    IconBlend(Icon, Icon, Offset),
}

#[derive(PartialEq, Eq)]
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
        theme::button_bar(Split::vertical(
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
            Button::with_text(verb)
        } else {
            left_is_small = right.is_some();
            Button::with_icon(Icon::new(theme::ICON_CANCEL))
        };
        let right = if let Some(verb) = right {
            Button::with_text(verb).styled(theme::button_confirm())
        } else {
            Button::with_icon(Icon::new(theme::ICON_CONFIRM)).styled(theme::button_confirm())
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
        let left = Button::with_icon(Icon::new(theme::ICON_CANCEL)).map(|msg| {
            (matches!(msg, ButtonMsg::Clicked)).then(|| CancelInfoConfirmMsg::Cancelled)
        });
        let total_height = theme::BUTTON_HEIGHT + theme::BUTTON_SPACING + theme::INFO_BUTTON_HEIGHT;
        FixedHeightBar::bottom(
            Split::horizontal(
                theme::INFO_BUTTON_HEIGHT,
                theme::BUTTON_SPACING,
                top,
                Split::vertical(theme::BUTTON_WIDTH, theme::BUTTON_SPACING, left, right),
            ),
            total_height,
        )
    }

    pub fn select_word(
        words: [T; 3],
    ) -> CancelInfoConfirm<
        T,
        impl Fn(ButtonMsg) -> Option<SelectWordMsg>,
        impl Fn(ButtonMsg) -> Option<SelectWordMsg>,
        impl Fn(ButtonMsg) -> Option<SelectWordMsg>,
    >
    where
        T: AsRef<str>,
    {
        let btn = move |i, word| {
            Button::with_text(word)
                .styled(theme::button_pin())
                .map(move |msg| {
                    (matches!(msg, ButtonMsg::Clicked)).then(|| SelectWordMsg::Selected(i))
                })
        };

        let [top, middle, bottom] = words;
        let total_height = 3 * theme::BUTTON_HEIGHT + 2 * theme::BUTTON_SPACING;
        FixedHeightBar::bottom(
            Split::horizontal(
                theme::BUTTON_HEIGHT,
                theme::BUTTON_SPACING,
                btn(0, top),
                Split::horizontal(
                    theme::BUTTON_HEIGHT,
                    theme::BUTTON_SPACING,
                    btn(1, middle),
                    btn(2, bottom),
                ),
            ),
            total_height,
        )
    }
}

pub enum CancelConfirmMsg {
    Cancelled,
    Confirmed,
}

type CancelInfoConfirm<T, F0, F1, F2> =
    FixedHeightBar<Split<Map<Button<T>, F0>, Split<Map<Button<T>, F1>, Map<Button<T>, F2>>>>;

type CancelConfirm<T, F0, F1> = FixedHeightBar<Split<Map<Button<T>, F0>, Map<Button<T>, F1>>>;

pub enum CancelInfoConfirmMsg {
    Cancelled,
    Info,
    Confirmed,
}

pub enum SelectWordMsg {
    Selected(usize),
}

#[derive(PartialEq, Eq)]
pub struct IconText {
    text: &'static str,
    icon: Icon,
}

impl IconText {
    const ICON_SPACE: i16 = 46;
    const ICON_MARGIN: i16 = 4;
    const TEXT_MARGIN: i16 = 6;

    pub fn new(text: &'static str, icon: Icon) -> Self {
        Self { text, icon }
    }

    pub fn paint(&self, area: Rect, style: &ButtonStyle, baseline_offset: i16) {
        let width = style.font.text_width(self.text);
        let height = style.font.text_height();

        let mut use_icon = false;
        let mut use_text = false;

        let mut icon_pos = Point::new(
            area.top_left().x + ((Self::ICON_SPACE + Self::ICON_MARGIN) / 2),
            area.center().y,
        );
        let mut text_pos =
            area.center() + Offset::new(-width / 2, height / 2) + Offset::y(baseline_offset);

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
            display::text(
                text_pos,
                self.text,
                style.font,
                style.text_color,
                style.button_color,
            );
        }

        if use_icon {
            self.icon
                .draw(icon_pos, CENTER, style.text_color, style.button_color);
        }
    }
}

pub struct FloatingButton<T> {
    inner: T,
    button: Floating<Button<&'static str>>,
}

pub enum FloatingButtonMsg<T> {
    ButtonClicked,
    Content(T),
}

impl<T> FloatingButton<T>
where
    T: Component,
{
    pub const fn top_right_corner(icon: Icon, inner: T) -> Self {
        Self {
            inner,
            button: Floating::top_right(
                theme::CORNER_BUTTON_SIDE,
                theme::CORNER_BUTTON_SPACING,
                Button::with_icon(icon)
                    .with_expanded_touch_area(Insets::uniform(theme::CORNER_BUTTON_SPACING))
                    .styled(theme::button_moreinfo()),
            ),
        }
    }

    pub fn inner(&self) -> &T {
        &self.inner
    }
}

impl<T> Component for FloatingButton<T>
where
    T: Component,
{
    type Msg = FloatingButtonMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.button.place(bounds);
        self.inner.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
            return Some(FloatingButtonMsg::ButtonClicked);
        }
        self.inner.event(ctx, event).map(FloatingButtonMsg::Content)
    }

    fn paint(&mut self) {
        self.inner.paint();
        self.button.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.inner.bounds(sink);
        self.button.bounds(sink);
    }
}

impl<T> Paginate for FloatingButton<T>
where
    T: Paginate,
{
    fn page_count(&mut self) -> usize {
        self.inner.page_count()
    }

    fn change_page(&mut self, to_page: usize) {
        self.inner.change_page(to_page)
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for FloatingButton<T>
where
    T: Component + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("FloatingButton");
        t.field("inner", self.inner());
        t.close();
    }
}
