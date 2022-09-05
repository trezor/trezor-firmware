use crate::ui::component::{Component, Event, EventCtx, Pad};
use crate::ui::constant::screen;
use crate::ui::{display};
use crate::ui::event::TouchEvent;
use crate::ui::geometry::{Point, Rect};
use crate::ui::model_tt::theme;






pub struct Homescreen<'a>{
    pad: Pad,
    device_name: &'a str,
}




pub enum HomescreenMsg {
    UnlockRequested,
}


impl<'a> Homescreen<'a> {

    pub fn new(device_name: &'a str) -> Self {

        let mut instance = Self {
            pad: Pad::with_background(theme::BG),
            device_name,
        };

        instance.pad.clear();
        instance
    }

    pub fn paint_unlocked(&self) {
        display::text_center(Point::new(screen().center().x, 35),"My Trezor",theme::FONT_BOLD, theme::GREY_LIGHT, theme::BG);
        display::avatar(screen().center(), theme::IMAGE_HOMESCREEN, theme::WHITE, theme::BLACK);
    }

    pub fn paint_not_connected(&self) {
        display::text_center(Point::new(screen().center().x, 35),"My Trezor",theme::FONT_BOLD, theme::GREY_LIGHT, theme::BG);
        display::avatar(screen().center(), theme::IMAGE_HOMESCREEN, theme::WHITE, theme::BLACK);

        let bar_area = Rect::new(Point::new(40, 100), Point::new(200, 140));
        let bar_area_in = Rect::new(Point::new(42, 102), Point::new(198, 138));

        display::rect_fill_rounded(
            bar_area, theme::GREY_LIGHT, theme::BG, 4);

        display::rect_fill_rounded(
            bar_area_in, theme::BG, theme::GREY_LIGHT, 4);


        // ui.display.text_center(
        //     ui.WIDTH // 2, 128, self.lock_label, ui.BOLD, ui.TITLE_GREY, ui.BG
        // )
        //
        // # "tap to unlock"
        // ui.display.text_center(
        //     ui.WIDTH // 2 + 10, 220, self.tap_label, ui.BOLD, ui.TITLE_GREY, ui.BG
        // )
        // ui.display.icon(45, 202, res.load(ui.ICON_CLICK), ui.TITLE_GREY, ui.BG)
    }
}

impl<'a> Component for Homescreen<'a> {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        bounds
    }

    fn event(&mut self, _: &mut EventCtx, event: Event) -> Option<Self::Msg> {

            if let Event::Touch(TouchEvent::TouchEnd(_)) = event {
                return Some(HomescreenMsg::UnlockRequested);
            }
            None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.paint_not_connected();
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {

    }
}
