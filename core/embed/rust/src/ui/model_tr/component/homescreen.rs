use crate::{
    strutil::StringType,
    trezorhal::usb::usb_configured,
    ui::{
        component::{Child, Component, Event, EventCtx, Label},
        display::{rect_fill, toif::Toif, Font, Icon},
        event::USBEvent,
        geometry::{Alignment2D, Insets, Offset, Point, Rect},
        layout::util::get_user_custom_image,
    },
};

use super::{
    super::constant, common::display_center, theme, ButtonController, ButtonControllerMsg,
    ButtonLayout, ButtonPos, CancelConfirmMsg,
};

const AREA: Rect = constant::screen();
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = constant::HEIGHT - 15;
const LABEL_AREA: Rect = AREA.split_top(LABEL_Y).1;
const LOCKED_INSTRUCTION_Y: i16 = 27;
const LOCKED_INSTRUCTION_AREA: Rect = AREA.split_top(LOCKED_INSTRUCTION_Y).1;
const LOGO_ICON_TOP_MARGIN: i16 = 12;
const LOCK_ICON_TOP_MARGIN: i16 = 12;
const NOTIFICATION_HEIGHT: i16 = 12;
const LABEL_OUTSET: i16 = 3;
const NOTIFICATION_FONT: Font = Font::NORMAL;
const NOTIFICATION_ICON: Icon = theme::ICON_WARNING;
const COINJOIN_CORNER: Point = AREA.top_right().ofs(Offset::new(-2, 2));

fn paint_default_image() {
    theme::ICON_LOGO.draw(
        TOP_CENTER + Offset::y(LOGO_ICON_TOP_MARGIN),
        Alignment2D::TOP_CENTER,
        theme::FG,
        theme::BG,
    );
}

pub struct Homescreen<T>
where
    T: StringType,
{
    // TODO label should be a Child in theory, but the homescreen image is not, so it is
    // always painted, so we need to always paint the label too
    label: Label<T>,
    notification: Option<(T, u8)>,
    /// Used for HTC functionality to lock device from homescreen
    invisible_buttons: Child<ButtonController<T>>,
}

impl<T> Homescreen<T>
where
    T: StringType + Clone,
{
    pub fn new(label: T, notification: Option<(T, u8)>) -> Self {
        let invisible_btn_layout = ButtonLayout::htc_none_htc("".into(), "".into());
        Self {
            label: Label::centered(label, theme::TEXT_BIG),
            notification,
            invisible_buttons: Child::new(ButtonController::new(invisible_btn_layout)),
        }
    }

    fn paint_homescreen_image(&self) {
        if let Ok(user_custom_image) = get_user_custom_image() {
            let toif_data = unwrap!(Toif::new(user_custom_image.as_ref()));
            toif_data.draw(TOP_CENTER, Alignment2D::TOP_CENTER, theme::FG, theme::BG);
        } else {
            paint_default_image();
        }
    }

    fn paint_notification(&self) {
        let baseline = TOP_CENTER + Offset::y(NOTIFICATION_FONT.line_height());
        if !usb_configured() {
            self.fill_notification_background();
            // TODO: fill warning icons here as well?
            display_center(baseline, &"NO USB CONNECTION", NOTIFICATION_FONT);
        } else if let Some((notification, _level)) = &self.notification {
            self.fill_notification_background();
            display_center(baseline, &notification.as_ref(), NOTIFICATION_FONT);
            // Painting warning icons in top corners when the text is short enough not to
            // collide with them
            let icon_width = NOTIFICATION_ICON.toif.width();
            let text_width = NOTIFICATION_FONT.text_width(notification.as_ref());
            if AREA.width() >= text_width + (icon_width + 1) * 2 {
                NOTIFICATION_ICON.draw(
                    AREA.top_left(),
                    Alignment2D::TOP_LEFT,
                    theme::FG,
                    theme::BG,
                );
                NOTIFICATION_ICON.draw(
                    AREA.top_right(),
                    Alignment2D::TOP_RIGHT,
                    theme::FG,
                    theme::BG,
                );
            }
        }
    }

    fn paint_label(&mut self) {
        // paint black background to place the label
        let mut outset = Insets::uniform(LABEL_OUTSET);
        // the margin at top is bigger (caused by text-height vs line-height?)
        // compensate by shrinking the outset
        outset.top -= 2;
        rect_fill(self.label.text_area().outset(outset), theme::BG);
        self.label.paint();
    }

    /// So that notification is well visible even on homescreen image
    fn fill_notification_background(&self) {
        rect_fill(AREA.split_top(NOTIFICATION_HEIGHT).0, theme::BG);
    }

    fn paint_warning_icons_in_top_corners(&self) {
        let warning_icon = theme::ICON_WARNING;
        warning_icon.draw(AREA.top_left(), Alignment2D::TOP_LEFT, theme::FG, theme::BG);
        warning_icon.draw(
            AREA.top_right(),
            Alignment2D::TOP_RIGHT,
            theme::FG,
            theme::BG,
        );
    }

    fn event_usb(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::USB(USBEvent::Connected(_)) = event {
            ctx.request_paint();
        }
    }
}

impl<T> Component for Homescreen<T>
where
    T: StringType + Clone,
{
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.label.place(LABEL_AREA);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        Self::event_usb(self, ctx, event);
        // HTC press of any button will lock the device
        if let Some(ButtonControllerMsg::Triggered(..)) = self.invisible_buttons.event(ctx, event) {
            return Some(());
        }
        None
    }

    fn paint(&mut self) {
        // Painting the homescreen image first, as the notification and label
        // should be "on top of it"
        self.paint_homescreen_image();
        self.paint_notification();
        self.paint_label();
    }
}

pub struct Lockscreen<T>
where
    T: StringType,
{
    label: Child<Label<T>>,
    instruction: Child<Label<T>>,
    /// Used for unlocking the device from lockscreen
    invisible_buttons: Child<ButtonController<T>>,
    /// Display coinjoin icon?
    coinjoin_icon: Option<Icon>,
    /// Screensaver mode (keep screen black)
    screensaver: bool,
}

impl<T> Lockscreen<T>
where
    T: StringType + Clone,
{
    pub fn new(label: T, bootscreen: bool, coinjoin_authorized: bool) -> Self {
        // Buttons will not be visible, we only need all three of them to be present,
        // so that even middle-click triggers the event.
        let invisible_btn_layout = ButtonLayout::arrow_armed_arrow("".into());
        let instruction_str = if bootscreen {
            "Click to Connect"
        } else {
            "Click to Unlock"
        };
        Lockscreen {
            label: Child::new(Label::centered(label, theme::TEXT_BIG)),
            instruction: Child::new(Label::centered(instruction_str.into(), theme::TEXT_NORMAL)),
            invisible_buttons: Child::new(ButtonController::new(invisible_btn_layout)),
            coinjoin_icon: coinjoin_authorized.then_some(theme::ICON_COINJOIN),
            screensaver: !bootscreen,
        }
    }
}

impl<T> Component for Lockscreen<T>
where
    T: StringType + Clone,
{
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

    fn paint(&mut self) {
        if self.screensaver {
            // keep screen blank
            return;
        }
        theme::ICON_LOCK.draw(
            TOP_CENTER + Offset::y(LOCK_ICON_TOP_MARGIN),
            Alignment2D::TOP_CENTER,
            theme::FG,
            theme::BG,
        );
        self.instruction.paint();
        self.label.paint();
        if let Some(i) = &self.coinjoin_icon {
            i.draw(
                COINJOIN_CORNER,
                Alignment2D::TOP_RIGHT,
                theme::FG,
                theme::BG,
            )
        }
    }
}

pub struct ConfirmHomescreen<T, F>
where
    T: StringType,
{
    title: Child<Label<T>>,
    buffer_func: F,
    buttons: Child<ButtonController<T>>,
}

impl<T, F> ConfirmHomescreen<T, F>
where
    T: StringType + Clone,
{
    pub fn new(title: T, buffer_func: F) -> Self {
        let btn_layout = ButtonLayout::cancel_none_text("CHANGE".into());
        ConfirmHomescreen {
            title: Child::new(Label::centered(title, theme::TEXT_BOLD)),
            buffer_func,
            buttons: Child::new(ButtonController::new(btn_layout)),
        }
    }
}

impl<'a, T, F> Component for ConfirmHomescreen<T, F>
where
    T: StringType + Clone,
    F: Fn() -> &'a [u8],
{
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

    fn paint(&mut self) {
        // Drawing the image full-screen first and then other things on top
        let buffer = (self.buffer_func)();
        if buffer.is_empty() {
            paint_default_image();
        } else {
            let toif_data = unwrap!(Toif::new(buffer));
            toif_data.draw(TOP_CENTER, Alignment2D::TOP_CENTER, theme::FG, theme::BG);
        };
        // Need to make all the title background black, so the title text is well
        // visible
        let title_area = self.title.inner().area();
        rect_fill(title_area, theme::BG);
        self.title.paint();
        self.buttons.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Homescreen<T>
where
    T: StringType,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.child("label", &self.label);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Lockscreen<T>
where
    T: StringType,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Lockscreen");
        t.child("label", &self.label);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, F> crate::trace::Trace for ConfirmHomescreen<T, F>
where
    T: StringType,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ConfirmHomescreen");
        t.child("title", &self.title);
    }
}
