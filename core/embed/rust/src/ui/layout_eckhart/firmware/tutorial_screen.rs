use crate::{
    time::{Duration, Stopwatch},
    translations::TR,
    ui::{
        component::{swipe_detect::SwipeConfig, Component, Event, EventCtx, Label, Timeout},
        display::{toif::Toif, Color},
        flow::Swipable,
        geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect},
        shape::{Bar, Renderer, ToifImage},
        util::{animation_disabled, Pager},
    },
};

use super::{
    super::{
        component::Button,
        constant::SCREEN,
        cshape::{render_loader_indeterminate, ScreenBorder},
        theme::{self, ScreenBackground},
    },
    ActionBar, ActionBarMsg,
};

// Duration of the loader animation
const LOADER_DURATION: Duration = Duration::from_secs(3);
// Loader animation + gradient duration
const TOTAL_DURATION: Duration = Duration::from_secs(5);
const LOADER_MAX_VAL: u16 = 1000;
const ICONS_PADDING: i16 = 15; // [px]
const LED_COLOR: Color = theme::LED_WHITE;

const TOP_INSET: i16 = 38;

pub enum TutorialWelcomeScreenMsg {
    Confirmed,
}

pub struct TutorialWelcomeScreen {
    text: Label<'static>,
    action_bar: ActionBar,
    /// Timer for the led color change
    #[cfg(feature = "rgb_led")]
    timer: Timeout,
    #[cfg(feature = "rgb_led")]
    led_color: Color,
    /// Stopwatch for the loader animation
    stopwatch: Stopwatch,
    border: ScreenBorder,
}

impl TutorialWelcomeScreen {
    pub fn new() -> Self {
        Self {
            text: Label::new(
                TR::tutorial__welcome_safe7.into(),
                Alignment::Start,
                theme::firmware::TEXT_REGULAR,
            )
            .top_aligned(),
            action_bar: ActionBar::new_timeout(Button::empty(), TOTAL_DURATION),
            #[cfg(feature = "rgb_led")]
            timer: Timeout::new(if animation_disabled() {
                0
            } else {
                LOADER_DURATION.to_millis()
            }),
            #[cfg(feature = "rgb_led")]
            led_color: Color::black(),
            stopwatch: Stopwatch::new_started(),
            border: ScreenBorder::new(theme::GREEN_LIME),
        }
    }
}

impl Component for TutorialWelcomeScreen {
    type Msg = TutorialWelcomeScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (rest, action_bar_area) = bounds.split_bottom(theme::ACTION_BAR_HEIGHT);
        let content_area = rest.inset(theme::SIDE_INSETS).inset(Insets::top(TOP_INSET));

        self.text.place(content_area);
        self.action_bar.place(action_bar_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ActionBarMsg::Confirmed) = self.action_bar.event(ctx, event) {
            return Some(TutorialWelcomeScreenMsg::Confirmed);
        }

        #[cfg(feature = "rgb_led")]
        if self.timer.event(ctx, event).is_some() {
            self.led_color = LED_COLOR;
            return None;
        }

        // TutorialWelcomeScreen reacts to ANIM_FRAME_TIMER
        match event {
            _ if animation_disabled() => {
                return None;
            }
            Event::Attach(_) => {
                ctx.request_anim_frame();
            }
            Event::Timer(EventCtx::ANIM_FRAME_TIMER) => {
                ctx.request_anim_frame();
                ctx.request_paint();
            }
            _ => {}
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        const ICON_TROPIC: Toif<'static> = theme::ICON_TROPIC.toif;
        // Center the icon in the action bar area in the full-screen component
        const ICON_POS: Point = SCREEN
            .bottom_center()
            .ofs(Offset::new(0, -theme::ACTION_BAR_HEIGHT / 2));

        if !self.stopwatch.is_running_within(LOADER_DURATION) {
            ScreenBackground::new(Some(LED_COLOR), None).render(target);
        }

        self.text.render(target);

        // Topic icon
        ToifImage::new(ICON_POS, ICON_TROPIC)
            .with_align(Alignment2D::CENTER)
            .with_fg(theme::GREY_EXTRA_LIGHT)
            .render(target);

        // Intro icon
        ToifImage::new(
            ICON_POS
                .sub(Point::new(0, ICONS_PADDING + ICON_TROPIC.height() / 2))
                .into(),
            theme::ICON_SECURED.toif,
        )
        .with_align(Alignment2D::BOTTOM_CENTER)
        .with_fg(theme::GREY_EXTRA_LIGHT)
        .render(target);

        if self.stopwatch.is_running_within(LOADER_DURATION) {
            let progress = self.stopwatch.elapsed() / LOADER_DURATION;
            let loader_val = (progress * LOADER_MAX_VAL as f32) as u16;
            render_loader_indeterminate(loader_val, &self.border, target);
        }

        #[cfg(feature = "rgb_led")]
        target.set_led_color(self.led_color);
    }
}

#[cfg(feature = "micropython")]
impl Swipable for TutorialWelcomeScreen {
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::new()
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for TutorialWelcomeScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("TutorialWelcomeScreen");
    }
}

const BUTTON_WIDTH: i16 = 10;
const BUTTON_HEIGHT: i16 = 96;
const BUTTON_TOP_PADDING: i16 = 75;

pub enum TutorialPowerScreenMsg {
    Cancelled,
    Confirmed,
}

pub struct TutorialPowerScreen {
    text: Label<'static>,
    action_bar: ActionBar,
}

impl TutorialPowerScreen {
    pub fn new() -> Self {
        Self {
            text: Label::new(
                TR::tutorial__power.into(),
                Alignment::Start,
                theme::firmware::TEXT_REGULAR,
            )
            .top_aligned(),
            action_bar: ActionBar::new_double(
                Button::with_icon(theme::ICON_CHEVRON_UP),
                Button::with_text(TR::buttons__continue.into()),
            ),
        }
    }
}

impl Component for TutorialPowerScreen {
    type Msg = TutorialPowerScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (rest, action_bar_area) = bounds.split_bottom(theme::ACTION_BAR_HEIGHT);
        let content_area = rest.inset(theme::SIDE_INSETS).inset(Insets::top(TOP_INSET));

        self.text.place(content_area);
        self.action_bar.place(action_bar_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self.action_bar.event(ctx, event) {
            Some(ActionBarMsg::Cancelled) => return Some(TutorialPowerScreenMsg::Cancelled),
            Some(ActionBarMsg::Confirmed) => return Some(TutorialPowerScreenMsg::Confirmed),
            _ => {}
        };

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let rect = Rect::from_center_and_size(
            Point::new(SCREEN.width(), BUTTON_TOP_PADDING + BUTTON_HEIGHT / 2),
            Offset::new(2 * BUTTON_WIDTH, BUTTON_HEIGHT),
        );
        Bar::new(rect)
            .with_radius(7)
            .with_bg(theme::GREEN_LIME)
            .render(target);
        self.text.render(target);
        self.action_bar.render(target);
    }
}

#[cfg(feature = "micropython")]
impl Swipable for TutorialPowerScreen {
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::new()
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for TutorialPowerScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("TutorialPowerScreen");
    }
}
