mod welcome;

use crate::ui::{
    component::Event,
    constant::screen,
    display::{self, Color},
    event::TouchEvent::{self, TouchEnd, TouchMove, TouchStart},
    geometry::{Alignment, Offset, Point, Rect},
    layout::simplified::{process_frame_event, show},
    shape::{self, render_on_display},
    ui_prodtest::{ProdtestLayoutType, ProdtestUI},
};

use crate::trezorhal::haptic::{play, play_custom, HapticEffect};
use crate::trezorhal::display::{DISPLAY_RESX, DISPLAY_RESY};

use heapless::Vec;

use super::{cshape::ScreenBorder, fonts, prodtest::welcome::Welcome, UIEckhart};

const HAPTIC_TEST_MATRIX_ROWS: u8 = 4;
const HAPTIC_TEST_MATRIX_COLS: u8 = 4;

#[derive(PartialEq)]
pub enum HapticFunc{
    RTP,
    Waveform,
}

pub enum CustomEffect{
    CustomEffect1 = 1,
    CustomEffect2 = 2,
    CustomEffect3 = 3,
    CustomEffect4 = 4,
    CustomEffect5 = 5,
    CustomEffect6 = 6,
    CustomEffect7 = 7,
    CustomEffect8 = 8,
    CustomEffect9 = 9,
    CustomEffect10 = 10,
    CustomEffect11 = 11,
    CustomEffect12 = 12,
    CustomEffect13 = 13,
    CustomEffect14 = 14,
    CustomEffect15 = 15,
    CustomEffect16 = 16,
}

impl CustomEffect {

    pub fn get_values(&self) -> (HapticFunc,i8,u16){
        match self {
            CustomEffect::CustomEffect1 => (HapticFunc::Waveform, 0, 1),
            CustomEffect::CustomEffect2 => (HapticFunc::Waveform, 0, 2),
            CustomEffect::CustomEffect3 => (HapticFunc::Waveform, 0, 3),
            CustomEffect::CustomEffect4 => (HapticFunc::Waveform, 0, 4),
            CustomEffect::CustomEffect5 => (HapticFunc::Waveform, 0, 5),
            CustomEffect::CustomEffect6 => (HapticFunc::Waveform, 0, 6),
            CustomEffect::CustomEffect7 => (HapticFunc::Waveform, 0, 7),
            CustomEffect::CustomEffect8 => (HapticFunc::Waveform, 0, 8),
            CustomEffect::CustomEffect9 => (HapticFunc::Waveform, 0, 9),
            CustomEffect::CustomEffect10 => (HapticFunc::Waveform, 0, 10),
            CustomEffect::CustomEffect11 => (HapticFunc::Waveform, 0, 11),
            CustomEffect::CustomEffect12 => (HapticFunc::Waveform, 0, 12),
            CustomEffect::CustomEffect13 => (HapticFunc::Waveform, 0, 13),
            CustomEffect::CustomEffect14 => (HapticFunc::Waveform, 0, 14),
            CustomEffect::CustomEffect15 => (HapticFunc::Waveform, 0, 15),
            CustomEffect::CustomEffect16 => (HapticFunc::RTP, 100,7),
        }
    }

    pub fn from_number(n:u8) -> Option<CustomEffect>{
        match n {
            1 => Some(CustomEffect::CustomEffect1),
            2 => Some(CustomEffect::CustomEffect2),
            3 => Some(CustomEffect::CustomEffect3),
            4 => Some(CustomEffect::CustomEffect4),
            5 => Some(CustomEffect::CustomEffect5),
            6 => Some(CustomEffect::CustomEffect6),
            7 => Some(CustomEffect::CustomEffect7),
            8 => Some(CustomEffect::CustomEffect8),
            9 => Some(CustomEffect::CustomEffect9),
            10 => Some(CustomEffect::CustomEffect10),
            11 => Some(CustomEffect::CustomEffect11),
            12 => Some(CustomEffect::CustomEffect12),
            13 => Some(CustomEffect::CustomEffect13),
            14 => Some(CustomEffect::CustomEffect14),
            15 => Some(CustomEffect::CustomEffect15),
            16 => Some(CustomEffect::CustomEffect16),
            _ => None,
        }
    }
}

#[allow(clippy::large_enum_variant)]
pub enum ProdtestLayout {
    Welcome(Welcome),
}

impl ProdtestLayoutType for ProdtestLayout {
    fn event(&mut self, event: Option<Event>) -> u32 {
        match self {
            ProdtestLayout::Welcome(f) => process_frame_event::<Welcome>(f, event),
        }
    }

    fn show(&mut self) -> u32 {
        match self {
            ProdtestLayout::Welcome(f) => show(f, false),
        }
    }

    fn init_welcome(id: Option<&'static str>) -> Self {
        Self::Welcome(Welcome::new(id))
    }
}

impl ProdtestUI for UIEckhart {
    type CLayoutType = ProdtestLayout;

    fn screen_prodtest_show_text(text: &str) {
        display::sync();
        render_on_display(None, Some(Color::black()), |target| {
            shape::Text::new(screen().center(), text, fonts::FONT_SATOSHI_REGULAR_22)
                .with_fg(Color::white())
                .with_align(Alignment::Center)
                .render(target);
        });

        display::refresh();
    }

    fn screen_prodtest_border() {
        display::sync();
        let border = ScreenBorder::new(Color::white());
        render_on_display(None, Some(Color::black()), |target| {
            border.render(u8::MAX, target);
        });

        display::refresh();
    }

    fn screen_prodtest_bars(colors: &str) {
        display::sync();

        let num_colors = colors.chars().count();

        let width = if num_colors > 0 {
            screen().width() / num_colors as i16
        } else {
            0
        };

        render_on_display(None, Some(Color::black()), |target| {
            for (i, c) in colors.chars().enumerate() {
                let color = match c {
                    'r' | 'R' => Color::rgb(255, 0, 0),
                    'g' | 'G' => Color::rgb(0, 255, 0),
                    'b' | 'B' => Color::rgb(0, 0, 255),
                    'w' | 'W' => Color::white(),
                    _ => Color::black(),
                };

                let area = Rect::from_top_left_and_size(
                    screen().top_left() + Offset::x(i as i16 * width),
                    Offset::new(width, screen().height()),
                );

                shape::Bar::new(area)
                    .with_fg(color)
                    .with_bg(color)
                    .render(target);
            }
        });

        display::refresh();
    }

    fn screen_prodtest_touch(area: Rect) {
        display::sync();
        render_on_display(None, Some(Color::black()), |target| {
            shape::Bar::new(area)
                .with_fg(Color::white())
                .with_bg(Color::white())
                .render(target);
        });

        display::refresh();
    }

    fn screen_prodtest_draw(events: Vec<TouchEvent, 256>) {
        display::sync();

        render_on_display(None, Some(Color::black()), |target| {
            for ev in events.iter() {
                match ev {
                    TouchStart(p) => {
                        shape::Bar::new(Rect::from_center_and_size(*p, Offset::new(3, 3)))
                            .with_bg(Color::rgb(0, 255, 0))
                            .render(target);
                    }
                    TouchMove(p) => {
                        shape::Bar::new(Rect::from_center_and_size(*p, Offset::new(1, 1)))
                            .with_bg(Color::white())
                            .render(target);
                    }
                    TouchEnd(p) => {
                        shape::Bar::new(Rect::from_center_and_size(*p, Offset::new(3, 3)))
                            .with_bg(Color::rgb(255, 0, 0))
                            .render(target);
                    }
                }
            }
        });

        display::refresh();
    }

    fn screen_prodtest_haptic_test(_pressed: bool, _x: u16, _y: u16) {
        display::sync();

        render_on_display(None, Some(Color::black()), |target| {

            for r in 0..HAPTIC_TEST_MATRIX_ROWS {
                for c in 0..HAPTIC_TEST_MATRIX_COLS {
                    let cell_width = (DISPLAY_RESX / HAPTIC_TEST_MATRIX_COLS as u32) as i16;
                    let cell_height: i16 = (DISPLAY_RESY / HAPTIC_TEST_MATRIX_ROWS as u32) as i16;
                    let x = c as i16 * cell_width;
                    let y = r as i16 * cell_height;
                    let effect_number = r * HAPTIC_TEST_MATRIX_COLS + c + 1;

                    let touch_area = Rect::from_top_left_and_size(
                        Point::new(x, y),
                        Offset::new(cell_width, cell_height),
                    );

                    let mut cell_color = Color::black();
                    if _pressed && touch_area.contains(Point::new(_x as i16, _y as i16)){
                        let (func, arg1, arg2) = CustomEffect::from_number(effect_number as u8).unwrap().get_values();


                        if func == HapticFunc::RTP{
                            play_custom(arg1, arg2);
                        } else {
                            play(HapticEffect::ButtonPress);
                        }
                        
                        cell_color = Color::rgb(200, 200, 200); // Light gray if pressed inside the cell
                    }

                    shape::Bar::new(touch_area)
                    .with_fg(Color::white())
                    .with_bg(cell_color)
                    .with_thickness(5)
                    .render(target);

                    // Draw number in the center of the cell
                    let cell_center = touch_area.center();
                    shape::Text::new(cell_center, &uformat!("{}", effect_number), fonts::FONT_SATOSHI_REGULAR_22)
                        .with_fg(Color::white())
                        .with_align(Alignment::Center)
                        .render(target);
                }
            }




        });

        display::refresh();
    }
}
