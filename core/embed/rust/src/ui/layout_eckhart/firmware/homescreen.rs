use crate::{
    error::Error,
    io::BinaryData,
    strutil::TString,
    time::{Duration, Stopwatch},
    translations::TR,
    trezorhal::ble,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Label, Never, Swipe, Timer},
        display::{image::ImageInfo, Color},
        geometry::{Alignment, Direction, Offset, Rect},
        layout::util::get_user_custom_image,
        lerp::Lerp,
        shape::{self, Renderer},
        util::animation_disabled,
    },
};

use super::{
    super::{
        component::{Button, ButtonContent, FuelGauge},
        fonts,
    },
    constant::{HEIGHT, SCREEN, WIDTH},
    theme::{self, firmware::button_homebar_style, ScreenBackground},
    ActionBar, ActionBarMsg, Hint,
};

#[cfg(feature = "rgb_led")]
use crate::ui::led::LedState;

type Notif = (TString<'static>, u8);
type NotifQueue = heapless::Vec<Notif, 4>;

/// Full-screen component for the homescreen and lockscreen.
pub struct Homescreen {
    /// Device name with shadow
    label: HomeLabel,
    /// Notification and background component
    notif_and_bg: NotifAndBgUI,
    notif_queue: NotifQueue,
    /// Home action bar
    action_bar: ActionBar,
    /// Background image
    image: Option<BinaryData<'static>>,
    /// Whether the homescreen is locked
    locked: bool,
    /// Whether the homescreen is a boot screen
    bootscreen: bool,
    /// Fuel gauge (battery status indicator) rendered in the `action_bar` area
    fuel_gauge: FuelGauge,
    /// Swipe component for vertical swiping
    swipe: Swipe,
    // swipe_config: SwipeConfig,
}

pub enum HomescreenMsg {
    Dismissed,
    Menu,
}

impl Homescreen {
    pub fn new(
        label: TString<'static>,
        _lockable: bool,
        locked: bool,
        bootscreen: bool,
        coinjoin_authorized: bool,
        notification: Option<Notif>,
    ) -> Result<Self, Error> {
        // Homebar
        let notif_level = notification.as_ref().map(|(_, l)| *l).unwrap_or(4);
        let (style_sheet, gradient) = button_homebar_style(notif_level);
        let btn = Button::new(Self::homebar_content(bootscreen, locked))
            .styled(style_sheet)
            .with_gradient(gradient);

        // Notification and Background
        let image = get_homescreen_image();
        let user_set_image = image.is_some();
        let mut notif_queue = NotifQueue::new();
        if let Some(notif) = notification {
            let _ = notif_queue.push(notif);
        }
        let notif_and_bg = NotifAndBgUI::new(user_set_image);

        Ok(Self {
            label: HomeLabel::new(label, user_set_image),
            notif_and_bg,
            notif_queue,
            action_bar: ActionBar::new_single(btn),
            image,
            locked,
            bootscreen,
            fuel_gauge: FuelGauge::homescreen_bar()
                .with_alignment(Alignment::Center)
                .with_font(fonts::FONT_SATOSHI_MEDIUM_26),
            swipe: Swipe::new().up(),
        })
    }

    fn homebar_content(bootscreen: bool, locked: bool) -> ButtonContent {
        let text = (bootscreen || locked).then_some(TR::lockscreen__unlock.into());
        ButtonContent::HomeBar(text)
    }

    fn event_fuel_gauge(&mut self, ctx: &mut EventCtx, event: Event) {
        if animation_disabled() {
            return;
        }

        self.fuel_gauge.event(ctx, event);
        let bar_content = if self.fuel_gauge.should_be_shown() {
            ButtonContent::Empty
        } else {
            Self::homebar_content(self.bootscreen, self.locked)
        };

        if let Some(b) = self.action_bar.right_button_mut() {
            b.set_content(bar_content)
        }
    }

    fn event_notification(&mut self, ctx: &mut EventCtx, event: Event) {
        if matches!(event, Event::Attach(_)) {
            if ble::is_connected() {
                // TODO: level?
                let _ = self.notif_queue.push((TR::words__connected.into(), 2));
            }
            self.notif_and_bg
                .update_notification(self.notif_queue.pop());
        }

        if let Some(NotifAndBgUIMsg::Done) = self.notif_and_bg.event(ctx, event) {
            self.notif_and_bg
                .update_notification(self.notif_queue.pop());
        }
    }
}

impl Component for Homescreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (rest, bar_area) = bounds.split_bottom(theme::ACTION_BAR_HEIGHT);
        let rest = self.notif_and_bg.place(rest);
        let label_area = rest.inset(theme::CONTENT_INSETS_NO_HEADER);

        self.label.place(label_area);
        self.action_bar.place(bar_area);
        self.fuel_gauge.place(bar_area);
        // Swipe component is placed in the action bar touch area
        self.swipe.place(self.action_bar.touch_area());
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.event_notification(ctx, event);
        self.event_fuel_gauge(ctx, event);

        let swipe_up = matches!(self.swipe.event(ctx, event), Some(Direction::Up));
        let homebar_tap = matches!(
            self.action_bar.event(ctx, event),
            Some(ActionBarMsg::Confirmed)
        );

        if swipe_up || homebar_tap {
            return if self.locked {
                Some(HomescreenMsg::Dismissed)
            } else {
                Some(HomescreenMsg::Menu)
            };
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(image) = self.image {
            if let ImageInfo::Jpeg(_) = ImageInfo::parse(image) {
                shape::JpegImage::new_image(SCREEN.top_left(), image).render(target);
            }
        }
        self.notif_and_bg.render(target);
        self.label.render(target);
        self.action_bar.render(target);
        if self.fuel_gauge.should_be_shown() {
            self.fuel_gauge.render(target);
        }
    }
}

/// Helper component to render a label with a shadow.
struct HomeLabel {
    label: Label<'static>,
    /// Label shadow, only rendered when custom homescreen image is set
    label_shadow: Option<Label<'static>>,
}

impl HomeLabel {
    const LABEL_SHADOW_OFFSET: Offset = Offset::uniform(2);
    const LABEL_TEXT_STYLE: TextStyle = theme::firmware::TEXT_BIG;
    const LABEL_SHADOW_TEXT_STYLE: TextStyle = TextStyle::new(
        fonts::FONT_SATOSHI_EXTRALIGHT_46,
        theme::BLACK,
        theme::BLACK,
        theme::BLACK,
        theme::BLACK,
    );

    fn new(label: TString<'static>, shadow: bool) -> Self {
        let label_primary = Label::left_aligned(label, Self::LABEL_TEXT_STYLE).top_aligned();
        let label_shadow = shadow
            .then_some(Label::left_aligned(label, Self::LABEL_SHADOW_TEXT_STYLE).top_aligned());
        Self {
            label: label_primary,
            label_shadow,
        }
    }

    fn inner(&self) -> &Label<'static> {
        &self.label
    }
}

impl Component for HomeLabel {
    type Msg = Never;
    fn place(&mut self, bounds: Rect) -> Rect {
        self.label.place(bounds);
        self.label_shadow
            .place(bounds.translate(Self::LABEL_SHADOW_OFFSET));
        bounds
    }
    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.label_shadow.render(target);
        self.label.render(target);
    }
}

/// Component to manage Homescreen notification and background rendering.
/// It handles notification appearance timing, LED color management, and
/// background rendering. These functionalities are encapsulated in a single
/// component to ensure synchronized behavior.
struct NotifAndBgUI {
    pub background: ScreenBackground,
    pub user_set_image: bool,
    pub state: NotifStatUI,
    pub hint: Option<Hint<'static>>,
    pub led_color: Option<Color>,
    pub timer: Timer,
}

enum NotifStatUI {
    Empty,
    /// Initial state, waiting before showing notification
    Initial,
    /// Notification appeared
    Appeared,
}

impl NotifAndBgUI {
    fn new(user_set_image: bool) -> Self {
        Self {
            background: ScreenBackground::new(Some(4)),
            user_set_image,
            state: NotifStatUI::Initial,
            hint: None,
            led_color: None,
            timer: Timer::new(),
        }
    }

    fn update_notification(&mut self, notif: Option<Notif>) {
        if let Some((text, level)) = notif {
            let led_color = Self::get_led_color(level);
            let hint = Self::get_hint(text, level);
            self.led_color = Some(led_color);
            self.hint = Some(hint);
            self.state = NotifStatUI::Initial;
        } else {
            self.led_color = None;
            self.hint = None;
            self.state = NotifStatUI::Empty;
        }
    }

    fn get_led_color(level: u8) -> Color {
        match level {
            0 => theme::LED_RED,
            1 => theme::LED_YELLOW,
            2 => theme::LED_BLUE,
            3 => theme::LED_GREEN_LIGHT,
            _ => theme::LED_WHITE,
        }
    }

    fn get_hint(text: TString<'static>, level: u8) -> Hint<'static> {
        match level {
            0 => Hint::new_warning_danger(text),
            1 => Hint::new_warning_neutral(text),
            2 => Hint::new_instruction(text, None),
            3 => Hint::new_instruction_green(text, Some(theme::ICON_INFO)),
            _ => Hint::new_instruction(text, Some(theme::ICON_INFO)),
        }
    }

    fn eval_led_sim_alpha(&self) -> u8 {
        u8::MAX
    }
}

enum NotifAndBgUIMsg {
    Done,
}

impl Component for NotifAndBgUI {
    type Msg = NotifAndBgUIMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let rest = if let Some(hint) = &mut self.hint {
            let (rest, hint_area) = bounds.split_bottom(hint.height());
            self.hint.place(hint_area);
            rest
        } else {
            bounds
        };
        rest
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match &mut self.state {
            NotifStatUI::Empty => {}
            NotifStatUI::Initial => {
                if !self.timer.is_running() {
                    self.timer.start(ctx, Duration::from_millis(500));
                }
                if self.timer.expire(event) {
                    self.state = NotifStatUI::Appeared;
                }
            }
            NotifStatUI::Appeared => {
                if !self.timer.is_running() {
                    self.timer.start(ctx, Duration::from_millis(3000));
                }
                if self.timer.expire(event) {
                    return Some(NotifAndBgUIMsg::Done);
                }
            }
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(led_color) = self.led_color {
            let led_alpha = self.eval_led_sim_alpha();
            self.background.render(target, Some((led_color, led_alpha)));

            #[cfg(feature = "rgb_led")]
            if matches!(self.state, NotifStatUI::Appeared) {
                target.set_led_state(LedState::Static(led_color));
            } else {
                target.set_led_state(LedState::Static(Color::black()));
            }
        } else {
            self.background.render(target, None);
        }
        self.hint.render(target);
    }
}

pub fn check_homescreen_format(image: BinaryData) -> bool {
    match ImageInfo::parse(image) {
        ImageInfo::Jpeg(info) => {
            info.width() == WIDTH && info.height() == HEIGHT && info.mcu_height() <= 16
        }
        _ => false,
    }
}

fn get_homescreen_image() -> Option<BinaryData<'static>> {
    if let Ok(image) = get_user_custom_image() {
        if check_homescreen_format(image) {
            return Some(image);
        }
    }
    None
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.child("label", self.label.inner());
    }
}
