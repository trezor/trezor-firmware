use crate::ui::component::{Component, Event, EventCtx, Pad};
use crate::ui::constant::screen;
use crate::ui::{display};
use crate::ui::event::TouchEvent;
use crate::ui::geometry::{Insets, Point, Rect};
use crate::ui::model_tt::theme;






pub struct LockScreen<'a>{
    pad: Pad,
    device_name: &'a str,
    avatar: &'a[u8],
    lock_label: Option<&'a str>,
    tap_label: Option<&'a str>,
}

pub enum LockScreenMsg {
    UnlockRequested,
}

impl<'a> LockScreen<'a> {

    pub fn new(
        device_name: &'a str,
        avatar: &'a[u8],
        lock_label: Option<&'a str>,
        tap_label: Option<&'a str>,
    ) -> Self {

        let mut instance = Self {
            pad: Pad::with_background(theme::BG),
            device_name,
            lock_label,
            tap_label,
            avatar,
        };

        instance.pad.clear();
        instance
    }

    // pub fn paint_unlocked(&self) {
    //     display::avatar(screen().center(), self.avatar, theme::WHITE, theme::BLACK);
    //     display::text_center(Point::new(screen().center().x, 35),self.device_name,theme::FONT_BOLD, theme::GREY_LIGHT, theme::BG);
    // }

    pub fn paint_locked(&self) {
        display::text_center(Point::new(screen().center().x, 35),self.device_name,theme::FONT_BOLD, theme::GREY_LIGHT, theme::BG);
        display::avatar(screen().center(), self.avatar, theme::WHITE, theme::BLACK);

        if let Some(label) = self.lock_label {
            let bar_area = Rect::new(Point::new(40, 100), Point::new(200, 140));
            let bar_area_in = bar_area.inset(Insets::uniform(2));

            display::rect_fill_rounded(
                bar_area, theme::GREY_LIGHT, theme::BG, 4);

            display::rect_fill_rounded(
                bar_area_in, theme::BG, theme::GREY_LIGHT, 4);

            display::text_center(
                Point::new(screen().center().x, 128), label, theme::FONT_BOLD, theme::GREY_LIGHT, theme::BG
            );
        }

        if let Some(label) = self.tap_label {
            // # "tap to unlock"
            display::text_center(
                Point::new(screen().center().x + 10, 220), label, theme::FONT_BOLD, theme::GREY_LIGHT, theme::BG
            );
            display::icon_top_left(Point::new(45, 202), theme::ICON_CLICK, theme::GREY_LIGHT, theme::BG)
        }
    }
}

impl<'a> Component for LockScreen<'a> {
    type Msg = LockScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        bounds
    }

    fn event(&mut self, _: &mut EventCtx, event: Event) -> Option<Self::Msg> {

            if let Event::Touch(TouchEvent::TouchEnd(_)) = event {
                return Some(LockScreenMsg::UnlockRequested);
            }
            None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.paint_locked();
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {

    }
}
