use crate::{
    io::BinaryData,
    strutil::TString,
    translations::TR,
    trezorhal::usb::usb_configured,
    ui::{
        component::{Child, Component, Event, EventCtx, Label},
        constant::{HEIGHT, WIDTH},
        display::{
            image::{ImageInfo, ToifFormat},
            Font, Icon,
        },
        geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect},
        layout::util::get_user_custom_image,
        shape,
        shape::Renderer,
    },
};

use super::{
    super::constant, theme, ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos,
    CancelConfirmMsg, LoaderMsg, ProgressLoader,
};

const AREA: Rect = constant::screen();
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = constant::HEIGHT - 18;
const LABEL_AREA: Rect = AREA.split_top(LABEL_Y).1;
const LOCKED_INSTRUCTION_Y: i16 = 27;
const LOCKED_INSTRUCTION_AREA: Rect = AREA.split_top(LOCKED_INSTRUCTION_Y).1;
const LOGO_ICON_TOP_MARGIN: i16 = 12;
const LOCK_ICON_TOP_MARGIN: i16 = 12;
const NOTIFICATION_HEIGHT: i16 = 12;
const LABEL_OUTSET: i16 = 3;
const NOTIFICATION_FONT: Font = Font::NORMAL_UPPER;
const NOTIFICATION_ICON: Icon = theme::ICON_WARNING;
const COINJOIN_CORNER: Point = AREA.top_right().ofs(Offset::new(-2, 2));

const HOLD_TO_LOCK_MS: u32 = 1000;

fn render_default_image<'s>(target: &mut impl Renderer<'s>) {
    shape::ToifImage::new(
        TOP_CENTER + Offset::y(LOGO_ICON_TOP_MARGIN),
        theme::ICON_LOGO.toif,
    )
    .with_align(Alignment2D::TOP_CENTER)
    .with_fg(theme::FG)
    .render(target);
}

enum CurrentScreen {
    EmptyAtStart,
    Homescreen,
    Loader,
}

pub struct Homescreen {
    // TODO label should be a Child in theory, but the homescreen image is not, so it is
    // always painted, so we need to always paint the label too
    label: Label<'static>,
    notification: Option<(TString<'static>, u8)>,
    custom_image: Option<BinaryData<'static>>,
    /// Used for HTC functionality to lock device from homescreen
    invisible_buttons: Child<ButtonController>,
    /// Holds the loader component
    loader: Option<Child<ProgressLoader>>,
    /// Whether to show the loader or not
    show_loader: bool,
    /// Which screen is currently shown
    current_screen: CurrentScreen,
}

impl Homescreen {
    pub fn new(
        label: TString<'static>,
        notification: Option<(TString<'static>, u8)>,
        loader_description: Option<TString<'static>>,
    ) -> Self {
        // Buttons will not be visible, we only need both left and right to be existing
        // so we can get the events from them.
        let invisible_btn_layout = ButtonLayout::text_none_text("".into(), "".into());
        let loader =
            loader_description.map(|desc| Child::new(ProgressLoader::new(desc, HOLD_TO_LOCK_MS)));

        Self {
            label: Label::centered(label, theme::TEXT_BIG),
            notification,
            custom_image: get_homescreen_image(),
            invisible_buttons: Child::new(ButtonController::new(invisible_btn_layout)),
            loader,
            show_loader: false,
            current_screen: CurrentScreen::EmptyAtStart,
        }
    }

    fn render_homescreen_image<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(image) = self.custom_image {
            shape::ToifImage::new_image(TOP_CENTER, image)
                .with_align(Alignment2D::TOP_CENTER)
                .with_fg(theme::FG)
                .render(target);
        } else {
            render_default_image(target);
        }
    }

    fn render_notification<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let baseline = TOP_CENTER + Offset::y(NOTIFICATION_FONT.line_height());
        if !usb_configured() {
            shape::Bar::new(AREA.split_top(NOTIFICATION_HEIGHT).0)
                .with_bg(theme::BG)
                .render(target);

            // TODO: fill warning icons here as well?
            TR::homescreen__title_no_usb_connection.map_translated(|t| {
                shape::Text::new(baseline, t)
                    .with_align(Alignment::Center)
                    .with_font(NOTIFICATION_FONT)
                    .render(target)
            });
        } else if let Some((notification, _level)) = &self.notification {
            shape::Bar::new(AREA.split_top(NOTIFICATION_HEIGHT).0)
                .with_bg(theme::BG)
                .render(target);

            notification.map(|c| {
                shape::Text::new(baseline, c)
                    .with_align(Alignment::Center)
                    .with_font(NOTIFICATION_FONT)
                    .render(target)
            });

            // Painting warning icons in top corners when the text is short enough not to
            // collide with them
            let icon_width = NOTIFICATION_ICON.toif.width();
            let text_width = notification.map(|c| NOTIFICATION_FONT.text_width(c));
            if AREA.width() >= text_width + (icon_width + 1) * 2 {
                shape::ToifImage::new(AREA.top_left(), NOTIFICATION_ICON.toif)
                    .with_align(Alignment2D::TOP_LEFT)
                    .with_fg(theme::FG)
                    .with_bg(theme::BG)
                    .render(target);
                shape::ToifImage::new(AREA.top_right(), NOTIFICATION_ICON.toif)
                    .with_align(Alignment2D::TOP_RIGHT)
                    .with_fg(theme::FG)
                    .with_bg(theme::BG)
                    .render(target);
            }
        }
    }

    fn render_label<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // paint black background to place the label
        let mut outset = Insets::uniform(LABEL_OUTSET);
        // the margin at top is bigger (caused by text-height vs line-height?)
        // compensate by shrinking the outset
        outset.top -= 5;
        shape::Bar::new(self.label.text_area().outset(outset))
            .with_bg(theme::BG)
            .render(target);

        self.label.render(target);
    }

    fn event_usb(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::USB(_) = event {
            ctx.request_paint();
        }
    }
}

impl Component for Homescreen {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.label.place(LABEL_AREA);
        self.loader.place(AREA);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        Self::event_usb(self, ctx, event);

        // Only care about button and loader events when there is a possibility of
        // locking the device
        if let Some(self_loader) = &mut self.loader {
            // When loader has completely grown, we can lock the device
            if let Some(LoaderMsg::GrownCompletely) = self_loader.event(ctx, event) {
                return Some(());
            }

            // Longer hold of any button will lock the device.
            // Normal/quick presses and releases will show/hide the loader.
            let button_event = self.invisible_buttons.event(ctx, event);
            if let Some(ButtonControllerMsg::Pressed(..)) = button_event {
                if !self.show_loader {
                    self.show_loader = true;
                    self_loader.mutate(ctx, |ctx, loader| {
                        loader.start(ctx);
                        ctx.request_paint();
                    });
                }
            }
            if let Some(ButtonControllerMsg::Triggered(..)) = button_event {
                self.show_loader = false;
                self_loader.mutate(ctx, |ctx, loader| {
                    loader.stop(ctx);
                    ctx.request_paint();
                });
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Redraw the whole screen when the screen changes (loader vs homescreen)
        if self.show_loader {
            self.loader.render(target);
        } else {
            // Painting the homescreen image first, as the notification and label
            // should be "on top of it"
            self.render_homescreen_image(target);
            self.render_notification(target);
            self.render_label(target);
        }
    }
}

pub struct Lockscreen<'a> {
    label: Child<Label<'a>>,
    instruction: Child<Label<'static>>,
    /// Used for unlocking the device from lockscreen
    invisible_buttons: Child<ButtonController>,
    /// Display coinjoin icon?
    coinjoin_icon: Option<Icon>,
    /// Screensaver mode (keep screen black)
    screensaver: bool,
}

impl<'a> Lockscreen<'a> {
    pub fn new(label: TString<'a>, bootscreen: bool, coinjoin_authorized: bool) -> Self {
        // Buttons will not be visible, we only need all three of them to be present,
        // so that even middle-click triggers the event.
        let invisible_btn_layout = ButtonLayout::arrow_armed_arrow("".into());
        let instruction_str = if bootscreen {
            TR::homescreen__click_to_connect
        } else {
            TR::homescreen__click_to_unlock
        };
        Self {
            label: Child::new(Label::centered(label, theme::TEXT_BIG)),
            instruction: Child::new(Label::centered(instruction_str.into(), theme::TEXT_NORMAL)),
            invisible_buttons: Child::new(ButtonController::new(invisible_btn_layout)),
            coinjoin_icon: coinjoin_authorized.then_some(theme::ICON_COINJOIN),
            screensaver: !bootscreen,
        }
    }
}

impl Component for Lockscreen<'_> {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.label.place(LABEL_AREA);
        self.instruction.place(LOCKED_INSTRUCTION_AREA);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Press of any button will unlock the device
        if let Some(ButtonControllerMsg::Triggered(..)) = self.invisible_buttons.event(ctx, event) {
            return Some(());
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.screensaver {
            // keep screen blank
            return;
        }
        shape::ToifImage::new(
            TOP_CENTER + Offset::y(LOCK_ICON_TOP_MARGIN),
            theme::ICON_LOCK.toif,
        )
        .with_align(Alignment2D::TOP_CENTER)
        .with_fg(theme::FG)
        .render(target);

        self.instruction.render(target);
        self.label.render(target);

        if let Some(icon) = &self.coinjoin_icon {
            shape::ToifImage::new(COINJOIN_CORNER, icon.toif)
                .with_align(Alignment2D::TOP_RIGHT)
                .with_fg(theme::FG)
                .render(target);
        }
    }
}

pub struct ConfirmHomescreen {
    title: Child<Label<'static>>,
    image: BinaryData<'static>,
    buttons: Child<ButtonController>,
}

impl ConfirmHomescreen {
    pub fn new(title: TString<'static>, image: BinaryData<'static>) -> Self {
        let btn_layout = ButtonLayout::cancel_none_text(TR::buttons__change.into());
        ConfirmHomescreen {
            title: Child::new(Label::left_aligned(title, theme::TEXT_BOLD_UPPER)),
            image,
            buttons: Child::new(ButtonController::new(btn_layout)),
        }
    }
}

impl Component for ConfirmHomescreen {
    type Msg = CancelConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (title_content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        let title_height = theme::TEXT_BOLD.text_font.line_height();
        let (title_area, _) = title_content_area.split_top(title_height);
        self.title.place(title_area);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Left button cancels, right confirms
        if let Some(ButtonControllerMsg::Triggered(pos, _)) = self.buttons.event(ctx, event) {
            match pos {
                ButtonPos::Left => return Some(CancelConfirmMsg::Cancelled),
                ButtonPos::Right => return Some(CancelConfirmMsg::Confirmed),
                _ => {}
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.image.is_empty() {
            render_default_image(target);
        } else {
            shape::ToifImage::new_image(TOP_CENTER, self.image)
                .with_align(Alignment2D::TOP_CENTER)
                .with_fg(theme::FG)
                .render(target);
        };
        // Need to make all the title background black, so the title text is well
        // visible
        let title_area = self.title.inner().area();

        shape::Bar::new(title_area)
            .with_bg(theme::BG)
            .render(target);

        self.title.render(target);
        self.buttons.render(target);
    }
}

pub fn check_homescreen_format(image: BinaryData) -> bool {
    match ImageInfo::parse(image) {
        ImageInfo::Toif(info) => {
            info.width() == WIDTH
                && info.height() == HEIGHT
                && info.format() == ToifFormat::GrayScaleEH
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

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.child("label", &self.label);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Lockscreen<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Lockscreen");
        t.child("label", &self.label);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ConfirmHomescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ConfirmHomescreen");
        t.child("title", &self.title);
    }
}
