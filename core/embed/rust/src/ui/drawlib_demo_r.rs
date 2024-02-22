use crate::ui::{
    display::{Color, Font},
    event::{ButtonEvent, PhysicalButton},
    geometry::{Insets, Offset, Point, Rect},
    model_tr::theme::bootloader::{ICON_ALERT, ICON_SPINNER, ICON_TRASH},
    shape,
    shape::Renderer,
};

use qrcodegen::{QrCode, QrCodeEcc, Version};

use crate::time;
use core::fmt::Write;
use heapless::String;

use crate::trezorhal::io::io_button_read;

const ICON_GOOGLE: &[u8] = include_res!("model_tt/res/fido/icon_google.toif");

fn render_screen_1<'r>(target: &mut impl Renderer<'r>) {
    let pt = Point::new(0, 0);
    shape::Text::new(pt, "TREZOR!!!")
        .with_fg(Color::rgb(255, 0, 0))
        .render(target);

    let pt = Point::new(40, 0);
    shape::Text::new(pt, "TREZOR!!!")
        .with_fg(Color::rgb(0, 255, 0))
        .render(target);

    let pt = Point::new(100, 0);
    shape::Text::new(pt, "TREZOR!!!")
        .with_fg(Color::rgb(0, 0, 255))
        .render(target);

    let pt = Point::new(80, 30);
    shape::Text::new(pt, "BITCOIN!")
        .with_font(Font::BOLD)
        .render(target);

    let pt = Point::new(80, 40);
    let s = "SatoshiLabs";
    shape::Text::new(pt, s)
        .with_fg(Color::rgb(0, 255, 255))
        .render(target);

    shape::Text::new(pt + Offset::new(1, 1), s)
        .with_fg(Color::rgb(255, 0, 0))
        .render(target);

    let pt = Point::new(-1, 25);
    shape::ToifImage::new(pt, ICON_TRASH.toif)
        .with_fg(Color::black())
        .with_bg(Color::white())
        .render(target);

    let pt = Point::new(80, 35);
    shape::ToifImage::new(pt, ICON_ALERT.toif).render(target);

    let pt = Point::new(95, 50);
    shape::ToifImage::new(pt, ICON_SPINNER.toif)
        .with_fg(Color::rgb(64, 192, 200))
        .render(target);
}

const QR_MAX_VERSION: Version = Version::new(10);

fn render_screen_2<'r>(target: &mut impl Renderer<'r>, ctx: &DemoContext) {
    let r = Rect::new(Point::new(4, 4), Point::new(64, 64));
    shape::Bar::new(r)
        .with_bg(Color::white())
        .with_radius(1)
        .render(target);

    if let Some(qr) = ctx.qr {
        shape::QrImage::new(r.inset(Insets::uniform(2)), qr)
            .with_fg(Color::white())
            .with_bg(Color::black())
            .render(target);
    }
}

fn render_screen_3<'r>(target: &mut impl Renderer<'r>, ctx: &DemoContext) {
    let pt = Point::new(64, 32);

    shape::Circle::new(pt, 20)
        .with_start_angle(ctx.counter - 360)
        .with_end_angle(ctx.counter)
        .with_bg(Color::white())
        .render(target);

    shape::Circle::new(pt, 20)
        .with_fg(Color::white())
        .with_thickness(1)
        .render(target);

    shape::Circle::new(pt, 13)
        .with_bg(Color::black())
        .render(target);

    let toif = ICON_ALERT.toif;
    let icon_tl = Point::new(pt.x - toif.width() / 2, pt.y - toif.height() / 2);
    shape::ToifImage::new(icon_tl, toif).render(target);

    let pt = Point::new(20, 55);
    shape::Text::new(pt, "Installing firmware")
        .with_fg(Color::white())
        .render(target);
}

fn render_screen_4<'r>(target: &mut impl Renderer<'r>, _ctx: &DemoContext) {
    let r = Rect::from_size(Offset::new(24, 18)).translate(Offset::new(4, 12));

    for y in 0..3 {
        for x in 0..4 {
            let radius = x + y * 4;
            let ofs = Offset::new(x * 32, y * 20);
            shape::Bar::new(r.translate(ofs))
                .with_radius(radius)
                .with_bg(Color::white())
                .render(target);
        }
    }
}

fn render_demo(ctx: &DemoContext) -> time::Duration {
    let split = ctx.split;
    let start_time = time::Instant::now();

    shape::render_on_display(
        Some(Rect::new(Point::new(0, 0), Point::new(128, 64))),
        Some(Color::black()),
        |target| {
            target.with_origin(Offset::new(split.x, split.y), &|target| {
                render_screen_4(target, ctx);
            });

            target.with_origin(Offset::new(split.x - 128, split.y), &|target| {
                render_screen_3(target, ctx);
            });

            target.with_origin(Offset::new(split.x - 256, split.y), &|target| {
                render_screen_2(target, ctx);
            });

            target.with_origin(Offset::new(split.x - 384, split.y), &|target| {
                render_screen_1(target);
            });
        },
    );

    time::Instant::now()
        .checked_duration_since(start_time)
        .unwrap()
}

fn render_info(duration: time::Duration) {
    shape::render_on_display(
        Some(Rect::new(Point::new(96, 0), Point::new(128, 10))),
        Some(Color::white()),
        |target| {
            let text_color = Color::black();

            let mut info = String::<128>::new();
            write!(info, "{}ms", duration.to_millis() as f32 / 1.0).unwrap();

            let font = Font::NORMAL;
            let pt = Point::new(0, font.vert_center(0, 10, "A"));
            shape::Text::new(pt, info.as_str())
                .with_fg(text_color)
                .with_font(font)
                .render(target);
        },
    );
}

struct DemoContext<'a> {
    qr: Option<&'a QrCode<'a>>,
    split: Point,
    counter: i16,
}

impl<'a> DemoContext<'a> {
    fn new(qr: Option<&'a QrCode>) -> Self {
        Self {
            qr,
            split: Point::zero(),
            counter: 0,
        }
    }

    fn update(&mut self, event: Option<ButtonEvent>) {
        match event {
            Some(ButtonEvent::ButtonPressed(PhysicalButton::Left)) => {
                self.split.x -= 32;
            }
            Some(ButtonEvent::ButtonPressed(PhysicalButton::Right)) => {
                self.split.x += 32;
            }

            _ => {}
        }

        self.counter += 1;
        if self.counter == 720 {
            self.counter = 0;
        }
    }
}

fn button_eval() -> Option<ButtonEvent> {
    let event = io_button_read();
    if event == 0 {
        return None;
    }

    let event_type = event >> 24;
    let event_btn = event & 0xFFFFFF;

    let event = ButtonEvent::new(event_type, event_btn);

    if let Ok(event) = event {
        return Some(event);
    }
    None
}

static mut FB: [u8; 128 * 64] = [0u8; 128 * 64];

#[no_mangle]
extern "C" fn drawlib_demo() {
    let mut outbuffer = [0u8; QR_MAX_VERSION.buffer_len()];
    let mut tempbuffer = [0u8; QR_MAX_VERSION.buffer_len()];

    let qr = unwrap!(QrCode::encode_text(
        "https://satoshilabs.com",
        &mut tempbuffer,
        &mut outbuffer,
        QrCodeEcc::Medium,
        Version::MIN,
        QR_MAX_VERSION,
        None,
        true,
    ));

    let mut ctx = DemoContext::new(Some(&qr));

    loop {
        ctx.update(button_eval());
        let duration = render_demo(&ctx);
        render_info(duration);
    }
}
