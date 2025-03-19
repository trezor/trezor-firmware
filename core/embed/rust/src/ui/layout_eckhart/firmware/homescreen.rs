use crate::{
    error::Error,
    io::BinaryData,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeConfig, text::TextStyle, Component, Event, EventCtx, Label, Never,
        },
        display::image::ImageInfo,
        flow::Swipable,
        geometry::{Insets, Offset, Rect},
        layout::util::get_user_custom_image,
        shape::{self, Renderer},
        util::{animation_disabled, Pager},
    },
};

use super::{
    super::{
        component::{Button, ButtonMsg},
        fonts,
    },
    constant::{HEIGHT, SCREEN, WIDTH},
    theme::{self, firmware::button_homebar_style, BLACK, GREEN_DARK, GREEN_EXTRA_DARK},
    ActionBar, ActionBarMsg, Hint, HoldToConfirmAnim,
};

/// Full-screen component for the homescreen and lockscreen.
pub struct Homescreen {
    /// Device name with shadow
    label: HomeLabel,
    /// Notification
    hint: Option<Hint<'static>>,
    /// Home action bar
    action_bar: ActionBar,
    /// Background image
    image: Option<BinaryData<'static>>,
    /// Whether the PIN is set and device can be locked
    lockable: bool,
    /// Whether the homescreen is locked
    locked: bool,
    /// Hold to lock button placed everywhere except the `action_bar`
    virtual_locking_button: Button,
    /// Hold to lock animation
    htc_anim: Option<HoldToConfirmAnim>,
}

pub enum HomescreenMsg {
    Dismissed,
    Menu,
}

impl Homescreen {
    pub fn new(
        label: TString<'static>,
        lockable: bool,
        locked: bool,
        bootscreen: bool,
        coinjoin_authorized: bool,
        notification: Option<(TString<'static>, u8)>,
    ) -> Result<Self, Error> {
        let image = get_homescreen_image();

        // Notification
        let mut notification_level = 4;
        let hint = if let Some((text, level)) = notification {
            notification_level = level;
            if notification_level == 0 {
                Some(Hint::new_warning_severe(text))
            } else {
                Some(Hint::new_instruction(text, Some(theme::ICON_INFO)))
            }
        } else if locked && coinjoin_authorized {
            Some(Hint::new_instruction_green(
                TR::coinjoin__do_not_disconnect,
                Some(theme::ICON_INFO),
            ))
        } else {
            None
        };

        // ActionBar button
        let button_style = button_homebar_style(notification_level);
        let button = if bootscreen {
            Button::with_homebar_content(Some(TR::lockscreen__tap_to_connect.into()))
                .styled(button_style)
        } else if locked {
            Button::with_homebar_content(Some(TR::lockscreen__tap_to_unlock.into()))
                .styled(button_style)
        } else {
            // TODO: Battery/Connectivity button content
            Button::with_homebar_content(None).styled(button_style)
        };

        let lock_duration = theme::LOCK_HOLD_DURATION;

        // Locking animation
        let htc_anim = if lockable && !animation_disabled() {
            Some(
                HoldToConfirmAnim::new()
                    .with_color(theme::GREY_LIGHT)
                    .with_duration(lock_duration)
                    .with_header_overlay(TR::progress__locking_device.into()),
            )
        } else {
            None
        };

        Ok(Self {
            label: HomeLabel::new(label),
            hint,
            action_bar: ActionBar::new_single(button),
            image,
            lockable,
            locked,
            virtual_locking_button: Button::empty().with_long_press(lock_duration),
            htc_anim,
        })
    }

    fn event_hold(&mut self, ctx: &mut EventCtx, event: Event) -> bool {
        self.htc_anim.event(ctx, event);
        if let Some(msg) = self.virtual_locking_button.event(ctx, event) {
            match msg {
                ButtonMsg::Pressed => {
                    if let Some(htc_anim) = &mut self.htc_anim {
                        htc_anim.start();
                        ctx.request_anim_frame();
                        ctx.request_paint();
                        ctx.disable_swipe();
                    }
                }
                ButtonMsg::Clicked => {
                    if let Some(htc_anim) = &mut self.htc_anim {
                        htc_anim.stop();
                        ctx.request_anim_frame();
                        ctx.request_paint();
                        ctx.enable_swipe();
                    } else {
                        // Animations disabled
                        return true;
                    }
                }
                ButtonMsg::Released => {
                    if let Some(htc_anim) = &mut self.htc_anim {
                        htc_anim.stop();
                        ctx.request_anim_frame();
                        ctx.request_paint();
                        ctx.enable_swipe();
                    }
                }
                ButtonMsg::LongPressed => {
                    return true;
                }
            }
        }
        false
    }
}

impl Component for Homescreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (rest, bar_area) = bounds.split_bottom(theme::ACTION_BAR_HEIGHT);
        let rest = if let Some(hint) = &mut self.hint {
            let (rest, hint_area) = rest.split_bottom(hint.height());
            hint.place(hint_area);
            rest
        } else {
            rest
        };
        let label_area = rest
            .inset(theme::SIDE_INSETS)
            .inset(Insets::top(theme::PADDING));

        self.label.place(label_area);
        self.action_bar.place(bar_area);
        // Locking button is placed everywhere except the action bar
        let locking_area = bounds.inset(Insets::bottom(self.action_bar.touch_area().height()));
        self.virtual_locking_button.place(locking_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ActionBarMsg::Confirmed) = self.action_bar.event(ctx, event) {
            if self.locked {
                return Some(HomescreenMsg::Dismissed);
            } else {
                return Some(HomescreenMsg::Menu);
            }
        }
        if self.lockable {
            Self::event_hold(self, ctx, event).then_some(HomescreenMsg::Dismissed)
        } else {
            None
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(image) = self.image {
            if let ImageInfo::Jpeg(_) = ImageInfo::parse(image) {
                shape::JpegImage::new_image(SCREEN.top_left(), image).render(target);
            }
        } else {
            render_default_hs(target);
        }
        self.label.render(target);
        self.hint.render(target);
        self.action_bar.render(target);
        self.htc_anim.render(target);
    }
}

/// Helper component to render a label with a shadow.
struct HomeLabel {
    label: Label<'static>,
    label_shadow: Label<'static>,
}

impl HomeLabel {
    const LABEL_SHADOW_OFFSET: Offset = Offset::uniform(2);
    const LABEL_TEXT_STYLE: TextStyle = theme::firmware::TEXT_BIG;
    const LABEL_SHADOW_TEXT_STYLE: TextStyle = TextStyle::new(
        fonts::FONT_SATOSHI_EXTRALIGHT_46,
        BLACK,
        BLACK,
        BLACK,
        BLACK,
    );

    fn new(label: TString<'static>) -> Self {
        let label_primary = Label::left_aligned(label, Self::LABEL_TEXT_STYLE).top_aligned();
        let label_shadow = Label::left_aligned(label, Self::LABEL_SHADOW_TEXT_STYLE).top_aligned();
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

pub fn check_homescreen_format(image: BinaryData) -> bool {
    match ImageInfo::parse(image) {
        ImageInfo::Jpeg(info) => {
            info.width() == WIDTH && info.height() == HEIGHT && info.mcu_height() <= 16
        }
        _ => false,
    }
}

fn render_default_hs<'a>(target: &mut impl Renderer<'a>) {
    shape::Bar::new(SCREEN)
        .with_fg(theme::BG)
        .with_bg(theme::BG)
        .render(target);

    shape::Circle::new(SCREEN.center(), 48)
        .with_fg(GREEN_DARK)
        .with_thickness(4)
        .render(target);
    shape::Circle::new(SCREEN.center(), 42)
        .with_fg(GREEN_EXTRA_DARK)
        .with_thickness(4)
        .render(target);
}

fn get_homescreen_image() -> Option<BinaryData<'static>> {
    if let Ok(image) = get_user_custom_image() {
        if check_homescreen_format(image) {
            return Some(image);
        }
    }
    None
}

#[cfg(feature = "micropython")]
impl Swipable for Homescreen {
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::default()
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.child("label", self.label.inner());
    }
}
